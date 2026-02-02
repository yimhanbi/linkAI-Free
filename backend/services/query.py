import argparse
import sys
import time
import threading
from contextlib import contextmanager

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SentenceTransformerRerank

from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore

from src.settings import configure_llamaindex


@contextmanager
def spinner(message: str = "처리 중"):
    stop = threading.Event()

    def run():
        frames = "|/-\\"
        i = 0
        while not stop.is_set():
            sys.stdout.write(f"\r{message}... {frames[i % len(frames)]}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(message) + 10) + "\r")
        sys.stdout.flush()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qdrant_url", default="http://localhost:6333", help="Qdrant REST URL")
    parser.add_argument("--collection", default="patents", help="Qdrant collection name")
    parser.add_argument("--q", required=True, help="질문")
    args = parser.parse_args()

    cfg = configure_llamaindex()

    client = QdrantClient(url=args.qdrant_url)
    vector_store = QdrantVectorStore(client=client, collection_name=args.collection, text_key="_node_content")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
    )

    retriever = index.as_retriever(cfg.retriever_top_k)

    reranker = SentenceTransformerRerank(
        model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_n=cfg.reranker_top_k,
    )

    qe = RetrieverQueryEngine(
        retriever=retriever,
        node_postprocessors=[reranker],
    )

    with spinner("RAG 검색/생성 중"):
        resp = qe.query(args.q)

    print("\n=== 답변 ===\n")
    print(str(resp))

    if getattr(resp, "source_nodes", None):
        print("\n=== 출처 ===\n")
        for sn in resp.source_nodes:
            meta = sn.node.metadata or {}
            patent_no = meta.get("patent_no") or "알 수 없음"
            application_no = meta.get("application_number") or "알 수 없음"
            title = meta.get("title") or "알 수 없음"
            filename = meta.get("source")
            print(f"공개번호: {patent_no}   출원번호: {application_no}")
            print(f"특허제목: {title}")
            print(f"파일명: {filename}")
            print("-----")

    return 0

# run: python -m src.query --collection patents --q "시트보수재 사용하는 특허 한국어로 알려줘"
if __name__ == "__main__":
    raise SystemExit(main())
