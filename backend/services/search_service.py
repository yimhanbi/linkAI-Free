
import time
import re
import json
from typing import List, Tuple, Optional

from llama_index.core import VectorStoreIndex, StorageContext, QueryBundle
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.schema import TextNode, NodeWithScore
from llama_index.core.postprocessor.types import BaseNodePostprocessor

from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MinShould
from llama_index.vector_stores.qdrant import QdrantVectorStore

import os

#-----------------------------------
#환경 변수
QDRANT_URL = os.getenv("QDRANT_URL")
COLLECTION_NAME = os.getenv("PATENTS_COLLECTION_NAME")
OLLAMA_BASE_URL= os.getenv("OLLAMA_BASE_URL")
LLM_MODEL= os.getenv("OLLAMA_LLM_MODEL")
EMBED_MODEL= os.getenv("OLLAMA_EMBED_MODEL")
RETRIEVER_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "30"))     # 벡터 검색 상위 K개
RERANKER_TOP_K = int(os.getenv("RERANKER_TOP_K", "6"))       # Reranking 후 상위 K개
METADATA_TOP_K = int(os.getenv("METADATA_TOP_K", "10"))      # 메타데이터 검색 상우 K개


#-------------------------------
#전역 변수
client:Optional[QdrantClient] = None
index: Optional[VectorStoreIndex]= None
retriever= None
reranker= None
synth= None 


#--------------------------------
#불용어 및 조사 정의
#--------------------------------

#검색 시 제외할 의미 없는 단어들
STOPWORDS = {
    "하다","해줘","알려줘","찾아줘","관련",
    "특허","발명","발명한"
}

# 한국어 조사 목록 
JOSA_SUFFIX = (
    "은","는","이","가","을","를",
    "의","에","에서","으로","와","과","도","만"
)


#--------------------------------

class MetaPrefixPostprocessor(BaseNodePostprocessor):
    
    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_str: Optional[str] = None,
    ) -> List[NodeWithScore]:
        
        for nws in nodes:
            node = nws.node
            meta = node.metadata or {}
            
            #메타데이터에서 특허 정보 추출
            patent_no = meta.get("patent_no","")
            application_no = meta.get("application_number","")
            title = meta.get("title","")
            
            #메타데이터에서 프리픽스 생성
            prefix= (
                f"[META]\n"
                f" - 공개번호: {patent_no}\n"
                f" - 출원번호: {application_no}\n"
                f" - 제목:  {title}\n"
                f"[/META]\n\n"
            )
            
            #기존 텍스트 가져오기
            orig = getattr(node,"text",None)
            if not orig:
                orig = node.get_content() or ""
            
            #이미 메타데이터가 있으면 건너뛰기
            if orig.startswith("[META]\n"):
                node.text= orig
            else:
                node.text = prefix + orig
        
        return nodes 


#--------------------------------------
# 토큰화 함수
#--------------------------------------
def simple_tokenize_korean(query: str) -> List[str]:
    # 1. 한글, 영문, 숫자만 추출
    raw_tokens = re.findall(r"[가-힣A-Za-z0-9]+", query)
    cleaned = []
    
    for tok in raw_tokens:
        # 2. 조사 제거 (끝에서부터 매칭)
        for josa in JOSA_SUFFIX:
            if tok.endswith(josa) and len(tok) > len(josa):
                tok = tok[:-len(josa)]  # 조사 부분 제거
                break
        
        # 3. 불용어 및 짧은 단어 제거
        if tok in STOPWORDS or len(tok) <= 1:
            continue
        
        cleaned.append(tok)
    
    return cleaned


#--------------------------------------
# 메타데이터 검색
#--------------------------------------
def qdrant_meta_search(
    tokens: List[str],
    limit: int,
) -> List[NodeWithScore]:
    

    if not tokens:
        return []

    # 각 토큰에 대해 여러 필드에서 검색 조건 생성
    should_conditions = []
    for t in tokens:
        should_conditions.extend([
            FieldCondition(key="applicants", match=MatchValue(value=t)),        # 출원인
            FieldCondition(key="inventors", match=MatchValue(value=t)),         # 발명자
            FieldCondition(key="agents", match=MatchValue(value=t)),           # 대리인
            FieldCondition(key="patent_no", match=MatchValue(value=t)),        # 공개번호
            FieldCondition(key="application_number", match=MatchValue(value=t)), # 출원번호
        ])

    # 필터 생성: section이 "doc_meta"이고, 위 조건 중 최소 1개 만족
    flt = Filter(
        must=[FieldCondition(key="section", match=MatchValue(value="doc_meta"))],
        min_should=MinShould(conditions=should_conditions, min_count=1),
    )

    # Qdrant 검색 실행
    hits, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=flt,
        limit=limit,
        with_payload=True,   # 메타데이터 포함
        with_vectors=False,  # 벡터는 불필요
    )

    # 결과를 NodeWithScore 형태로 변환
    out = []
    for h in hits:
        payload = h.payload or {}
        raw = payload.get("_node_content") or payload.get("text") or ""

        # JSON 형태면 파싱
        text = raw
        if isinstance(raw, str) and raw.startswith("{"):
            try:
                obj = json.loads(raw)
                text = obj.get("text") or obj.get("_node_content") or raw
            except Exception:
                text = raw

        # 메타데이터 추출 (text, _node_content 제외)
        meta = {k: v for k, v in payload.items() if k not in ("text", "_node_content")}
        
        # TextNode 생성
        node = TextNode(text=text, metadata=meta)
        out.append(NodeWithScore(node=node, score=0.0))
    
    return out


#--------------------------------------
# 출처 추출
#--------------------------------------
def print_sources(nodes: List[NodeWithScore]) -> List[dict]:
    """
     combined_nodes에서 출처(공개번호, 출원번호, 제목)를
    중복 제거해서 리스트로 출력
    """
    
    seen = set()  # 중복 체크용
    results = []

    for nws in nodes:
        meta = nws.node.metadata or {}
        patent_no = meta.get("patent_no")
        application_no = meta.get("application_number")
        title = meta.get("title")

        # 정보가 하나도 없으면 건너뛰기
        if not (patent_no or application_no or title):
            continue

        # 중복 체크 (세 필드 조합으로 판단)
        key = (patent_no, application_no, title)
        if key in seen:
            continue

        seen.add(key)
        results.append(key)
        
        
    if not results:
        print("\n===출처 ===\n없음")
    return results


    print("\n=== 출처 ===\n")
    for i, (pno, ano, title) in enumerate(results, 1):
        print(f"[{i}] 공개번호: {pno}")
        print(f"    출원번호: {ano}")
        print(f"    특허제목: {title}")
        print()





#--------------------------------------
# 초기화 함수
#--------------------------------------
async def initialize_llamaindex():
    global client, index, retriever, reranker, synth
    
    # 1. 시작 시간 기록 (에러 방지 핵심!)
    start = time.time()
    
    # 환경 변수 확인
    openai_key = os.getenv("OPENAI_API_KEY")
    llm_name = "gpt-4o-mini" if openai_key else LLM_MODEL
    print(f"▶ Initializing LlamaIndex with {llm_name}...")
    
    try:
        # 2. LLM 설정
        if openai_key:
            from llama_index.llms.openai import OpenAI
            os.environ["OPENAI_API_KEY"] = openai_key
            Settings.llm = OpenAI(model="gpt-4o-mini")
            print("🚀 LLM Mode: OpenAI (gpt-4o-mini)")
        else:
            Settings.llm = Ollama(
                model=LLM_MODEL,
                base_url=OLLAMA_BASE_URL,
                request_timeout=300.0 
            )
            print(f"🏠 LLM Mode: Ollama ({LLM_MODEL})")

        # 3. Embedding 설정
        Settings.embed_model = OllamaEmbedding(
            model_name=EMBED_MODEL,
            base_url=OLLAMA_BASE_URL
        )
# async def initialize_llamaindex():
#     global client, index, retriever, reranker, synth
    
#     start = time.time()
#     print(f"▶ Initializing LlamaIndex with Ollama ({LLM_MODEL})...")
    
    
#     try:
#         #Ollama 모델 LlamaIndex 전역 설정에 주입 --
#         #1. LLM 설정 (답변 생성용)
#         Settings.llm = Ollama(
#             model = LLM_MODEL,
#             base_url = OLLAMA_BASE_URL,
#             request_timeout=600.0,
#         )
        
#         #2. Embedding 설정 
#         Settings.embed_model = OllamaEmbedding(
#             model_name = EMBED_MODEL,
#             base_url = OLLAMA_BASE_URL,
#             request_timeout=900.0,
#         )
        
        # --------------------------------------------------
        
       # 4. Qdrant 클라이언트 연결
        client = QdrantClient(url=QDRANT_URL, timeout=60)
        print("▶ Qdrant Connected")
        
        # 5. Vector Store & Index 생성
        vector_store = QdrantVectorStore(client=client, collection_name=COLLECTION_NAME)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
        )
        
        # 6. 검색 및 엔진 구성 요소 초기화
        retriever = index.as_retriever(similarity_top_k=RETRIEVER_TOP_K)
        
        reranker = SentenceTransformerRerank(
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            top_n=RERANKER_TOP_K
            # device = "cpu"
        )
        
        synth = get_response_synthesizer(
            response_mode="compact"
        )
        
        # 7. 소요 시간 계산
        elapsed = time.time() - start
        print(f"✅ LlamaIndex engine initialized in {elapsed:.2f}초")
        
    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        raise e
    


#--------------------------------------
# 쿼리 실행 함수
#--------------------------------------
async def run_llamaindex_query(query: str, top_k: int = 30) -> Tuple[str, List[dict]]:
    overall_start = time.time()
    
    print(f"\n{'#'*70}")
    print(f"🔍 [LlamaIndex RAG 시작] Query: '{query}'")
    print(f"{'#'*70}")
    
    try:
        # 1. 쿼리 번들 생성
        qb = QueryBundle(query)
        
        # 2. 벡터 검색
        retrieve_start = time.time()
        base_nodes = retriever.retrieve(qb)
        retrieve_elapsed = time.time() - retrieve_start
        print(f"⏱️  [1단계: 벡터 검색] {retrieve_elapsed:.2f}초 → {len(base_nodes)}개 노드")
        
        # 3. Reranking
        rerank_start = time.time()
        reranked_nodes = reranker.postprocess_nodes(base_nodes, query_bundle=qb)
        rerank_elapsed = time.time() - rerank_start
        print(f"⏱️  [2단계: Reranking] {rerank_elapsed:.2f}초 → {len(reranked_nodes)}개 노드")
        
        # 4. 메타데이터 검색 (가장 의심되는 구간 1)
        meta_start = time.time()
        tokens = simple_tokenize_korean(query)
        print(f"🔎 [토큰화 완료] {tokens}")
        
        # qdrant_meta_search 내부에서 에러가 나는지 확인
        meta_nodes = qdrant_meta_search(tokens=tokens, limit=METADATA_TOP_K)
        meta_elapsed = time.time() - meta_start
        print(f"⏱️  [3단계: 메타데이터 검색] {meta_elapsed:.2f}초 → {len(meta_nodes)}개 노드")
        
        # 5. 노드 결합 및 프리픽스 추가
        combine_start = time.time()
        combined_nodes = list(reranked_nodes) + list(meta_nodes)
        
        postprocessor = MetaPrefixPostprocessor()
        combined_nodes = postprocessor.postprocess_nodes(combined_nodes, query_str=query)
        combine_elapsed = time.time() - combine_start
        print(f"⏱️  [4단계: 노드 결합] {combine_elapsed:.2f}초")
        
        # 6. LLM 답변 생성 (가장 의심되는 구간 2 - OpenAI 호출)
        llm_start = time.time()
        print(f"🧠 [5단계: LLM 답변 생성 중...]")
        
        # 여기서 멈춘다면 API 키 문제나 네트워크 문제입니다.
        resp = synth.synthesize(qb, combined_nodes)
        answer = str(resp)
        
        llm_elapsed = time.time() - llm_start
        print(f"⏱️  [5단계: LLM 답변] {llm_elapsed:.2f}초")
        
        # 7. 출처 추출
        sources = print_sources(combined_nodes)
        overall_elapsed = time.time() - overall_start
        print(f"✅ [전체 완료] {overall_elapsed:.2f}초\n")
        
        return answer, sources

    except Exception as e:
        # 에러 발생 시 상세 로그를 터미널에 강제로 찍습니다.
        print("\n" + "!"*30 + " ERROR 발생 " + "!"*30)
        import traceback
        traceback.print_exc() # 어느 줄에서 에러가 났는지 알려줌
        print("!"*72 + "\n")
        # 에러를 다시 던져서 500 응답이 나가게 함
        raise e


    
# 수정 후 (방어 코드 적용)
async def close(self):
    # hasattr를 사용하여 변수가 실제로 존재하는지 확인하고 닫습니다.
    if hasattr(self, 'client_openai_async') and self.client_openai_async:
        await self.client_openai_async.close()
    
    # Qdrant 클라이언트 등 다른 연결도 안전하게 닫기
    if hasattr(self, 'client') and self.client:
        self.client.close()
        
    print("✅ 챗봇 검색 서비스가 안전하게 종료되었습니다.")
    