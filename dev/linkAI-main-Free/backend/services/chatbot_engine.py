import os
import asyncio
import re
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from functools import lru_cache

# LlamaIndex & Qdrant 관련
from llama_index.core import VectorStoreIndex, StorageContext, QueryBundle
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.schema import TextNode, NodeWithScore
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.llms.ollama import Ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MinShould
from llama_index.vector_stores.qdrant import QdrantVectorStore
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class LlamaIndexConfig:
    retriever_top_k: int = 20
    reranker_top_k: int = 10
    metadata_top_k: int = 20

def load_llamaindex_config() -> LlamaIndexConfig:
    retriever_top_k_raw: str = (os.getenv("RETRIEVER_TOP_K") or "").strip()
    reranker_top_k_raw: str = (os.getenv("RERANKER_TOP_K") or "").strip()
    metadata_top_k_raw: str = (os.getenv("METADATA_TOP_K") or "").strip()
    retriever_top_k: int = int(retriever_top_k_raw) if retriever_top_k_raw.isdigit() else 20
    reranker_top_k: int = int(reranker_top_k_raw) if reranker_top_k_raw.isdigit() else 10
    metadata_top_k: int = int(metadata_top_k_raw) if metadata_top_k_raw.isdigit() else 20
    return LlamaIndexConfig(
        retriever_top_k=retriever_top_k,
        reranker_top_k=reranker_top_k,
        metadata_top_k=metadata_top_k,
    )

# --- 전처리 유틸리티 ---
STOPWORDS = {"하다", "해줘", "알려줘", "찾아줘", "관련", "특허", "발명", "발명한"}
JOSA_SUFFIX = ("은", "는", "이", "가", "을", "를", "의", "에", "에서", "으로", "와", "과", "도", "만")

def simple_tokenize_korean(query: str) -> List[str]:
    raw_tokens = re.findall(r"[가-힣A-Za-z0-9]+", query)
    cleaned = []
    for tok in raw_tokens:
        for josa in JOSA_SUFFIX:
            if tok.endswith(josa) and len(tok) > len(josa):
                tok = tok[:-len(josa)]
                break
        if tok in STOPWORDS or len(tok) <= 1:
            continue
        cleaned.append(tok)
    return cleaned

# --- 메타데이터 주입 프로세서 ---
class MetaPrefixPostprocessor(BaseNodePostprocessor):
    def _postprocess_nodes(self, nodes: List[NodeWithScore], query_bundle: QueryBundle) -> List[NodeWithScore]:
        for nws in nodes:
            meta = nws.node.metadata or {}
            prefix = (
                f"[META]\n"
                f"- 공개번호: {meta.get('patent_no', '')}\n"
                f"- 출원번호: {meta.get('application_number', '')}\n"
                f"- 제목: {meta.get('title', '')}\n"
                f"[/META]\n\n"
            )
            orig = nws.node.get_content() or ""
            if not orig.startswith("[META]\n"):
                nws.node.text = prefix + orig
        return nodes

# --- 메인 챗봇 엔진 ---
class ChatbotEngine:
    def __init__(self):
        self.cfg: LlamaIndexConfig = load_llamaindex_config()

        qdrant_url: str = (os.getenv("QDRANT_URL") or "http://localhost:6333").strip()
        self.collection: str = (os.getenv("QDRANT_COLLECTION_NAME") or "patents_v2").strip()
        self.client: QdrantClient = QdrantClient(url=qdrant_url)
        
        # 2. Vector Store 및 Index 설정
        vector_store: QdrantVectorStore = QdrantVectorStore(client=self.client, collection_name=self.collection)
        self.index: VectorStoreIndex = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=StorageContext.from_defaults(vector_store=vector_store),
        )
        
        # 3. 리랭커 및 답변 합성기 설정
        self.reranker: SentenceTransformerRerank = SentenceTransformerRerank(
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            top_n=self.cfg.reranker_top_k,
        )
        
        # LLM 설정: Ollama 사용 (환경변수로 모델명 지정 가능)
        ollama_model: str = (os.getenv("OLLAMA_MODEL") or "llama3.2").strip()
        ollama_base_url: str = (os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").strip()
        llm = Ollama(model=ollama_model, base_url=ollama_base_url, request_timeout=300.0)
        self.synth = get_response_synthesizer(llm=llm)

        self.mongo_uri: Optional[str] = (os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or "").strip() or None
        self.db_name: str = (os.getenv("DB_NAME") or "moaai_db").strip()
        self.chat_history_ttl_days: int = int((os.getenv("CHAT_HISTORY_TTL_DAYS") or "30").strip() or "30")
        self.mongo_client: Optional[AsyncIOMotorClient] = AsyncIOMotorClient(self.mongo_uri) if self.mongo_uri else None
        self.db = self.mongo_client[self.db_name] if self.mongo_client else None

        self._memory_sessions: Dict[str, Dict[str, Any]] = {}

    async def answer(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """FastAPI 라우터에서 호출되는 비동기 메서드 (query, session_id 호환)"""
        current_session_id: str = session_id or uuid.uuid4().hex[:12]
        try:
            # 1. 무거운 RAG 로직은 스레드풀에서 실행 (이벤트 루프 차단 방지)
            answer_text, combined_nodes = await asyncio.to_thread(self._run_hybrid_query, query)
            
            # 2. 출처 데이터 정리
            sources = self._extract_sources(combined_nodes)

            await self._save_message(current_session_id, query, answer_text)

            return {
                "answer": answer_text,
                "sources": sources,
                "session_id": current_session_id,
            }
        except Exception as e:
            logger.exception("chatbot_engine_answer_failed err=%r", e)
            await self._save_message(current_session_id, query, "데이터를 처리하는 중 오류가 발생했습니다.")
            return {"answer": "데이터를 처리하는 중 오류가 발생했습니다.", "sources": [], "session_id": current_session_id}

    async def get_all_session(self, limit: int = 100) -> List[Dict[str, Any]]:
        if self.db:
            collection = self.db["chat_history"]
            cursor = (
                collection.find({}, {"_id": 0, "session_id": 1, "title": 1, "updated_at": 1})
                .sort("updated_at", -1)
                .limit(limit)
            )
            sessions: List[Dict[str, Any]] = await cursor.to_list(length=limit)
            return sessions
        sessions: List[Dict[str, Any]] = list(self._memory_sessions.values())
        sessions.sort(key=lambda x: x.get("updated_at") or datetime.min, reverse=True)
        return sessions[:limit]

    async def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        if self.db:
            collection = self.db["chat_history"]
            doc = await collection.find_one({"session_id": session_id}, {"_id": 0, "messages": 1})
            messages = doc.get("messages") if doc else None
            return messages if isinstance(messages, list) else []
        session = self._memory_sessions.get(session_id)
        messages = session.get("messages") if session else None
        return messages if isinstance(messages, list) else []

    async def delete_session(self, session_id: str) -> bool:
        if self.db:
            collection = self.db["chat_history"]
            result = await collection.delete_one({"session_id": session_id})
            return bool(getattr(result, "deleted_count", 0))
        return bool(self._memory_sessions.pop(session_id, None))

    def _run_hybrid_query(self, query: str) -> Tuple[str, List[NodeWithScore]]:
        """하이브리드 검색 및 답변 생성 핵심 로직"""
        qb = QueryBundle(query)
        
        # Path A: 벡터 기반 검색 및 리랭킹
        retriever = self.index.as_retriever(similarity_top_k=self.cfg.retriever_top_k)
        base_nodes = retriever.retrieve(qb)
        reranked_nodes = self.reranker.postprocess_nodes(base_nodes, query_bundle=qb)

        # Path B: 키워드 기반 메타데이터 검색
        tokens = simple_tokenize_korean(query)
        meta_nodes = self._qdrant_meta_search(tokens, limit=self.cfg.metadata_top_k)

        # 통합 및 후처리
        combined_nodes = list(reranked_nodes) + list(meta_nodes)
        meta_prefix = MetaPrefixPostprocessor()
        processed_nodes = meta_prefix.postprocess_nodes(combined_nodes, query_bundle=qb)

        # 답변 합성
        response = self.synth.synthesize(qb, processed_nodes)
        return str(response), processed_nodes

    def _qdrant_meta_search(self, tokens: List[str], limit: int) -> List[NodeWithScore]:
        """Qdrant Scroll API를 이용한 키워드 필터링 검색"""
        if not tokens:
            return []

        should_conditions = []
        for t in tokens:
            fields = ["applicants", "inventors", "agents", "patent_no", "application_number"]
            should_conditions.extend([FieldCondition(key=f, match=MatchValue(value=t)) for f in fields])

        flt = Filter(
            must=[FieldCondition(key="section", match=MatchValue(value="doc_meta"))],
            min_should=MinShould(conditions=should_conditions, min_count=1),
        )

        hits, _ = self.client.scroll(
            collection_name=self.collection,
            scroll_filter=flt,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        out = []
        for h in hits:
            payload = h.payload or {}
            # 노드 텍스트 추출
            raw = payload.get("_node_content") or payload.get("text") or ""
            if isinstance(raw, str) and raw.startswith("{"):
                try:
                    obj = json.loads(raw)
                    text = obj.get("text") or obj.get("_node_content") or raw
                except: text = raw
            else: text = raw

            meta = {k: v for k, v in payload.items() if k not in ("text", "_node_content")}
            out.append(NodeWithScore(node=TextNode(text=text, metadata=meta), score=0.0))
        return out

    async def _save_message(self, session_id: str, user_query: str, ai_answer: str) -> None:
        now_dt: datetime = datetime.utcnow()
        title: str = (user_query[:25] + "...") if len(user_query) > 25 else user_query

        if self.db:
            collection = self.db["chat_history"]
            await collection.update_one(
                {"session_id": session_id},
                {
                    "$setOnInsert": {
                        "session_id": session_id,
                        "created_at": now_dt,
                        "messages": [
                            {"role": "user", "content": user_query, "timestamp": time.time()},
                            {"role": "assistant", "content": ai_answer, "timestamp": time.time()},
                        ],
                    },
                    "$set": {
                        "updated_at": now_dt,
                        "title": title,
                        "expires_at": now_dt + timedelta(days=self.chat_history_ttl_days),
                    },
                },
                upsert=True,
            )
            return

        session = self._memory_sessions.get(session_id)
        if not session:
            session = {"session_id": session_id, "created_at": now_dt, "messages": []}
            self._memory_sessions[session_id] = session
        session["messages"].extend(
            [
                {"role": "user", "content": user_query, "timestamp": time.time()},
                {"role": "assistant", "content": ai_answer, "timestamp": time.time()},
            ]
        )
        session["updated_at"] = now_dt
        session["title"] = title

    def _extract_sources(self, nodes: List[NodeWithScore]) -> List[Dict]:
        seen = set()
        results = []
        for nws in nodes:
            meta = nws.node.metadata or {}
            pno, ano, title = meta.get("patent_no"), meta.get("application_number"), meta.get("title")
            if not (pno or ano or title): continue
            
            key = (pno, ano, title)
            if key not in seen:
                seen.add(key)
                results.append({"patent_no": pno, "application_no": ano, "title": title})
        return results

@lru_cache
def get_chatbot_engine():
    return ChatbotEngine()