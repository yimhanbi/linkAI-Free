import os
import argparse
import glob
import logging

from llama_index.core import VectorStoreIndex, StorageContext
from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore

from services.settings import configure_llamaindex
from services.loader import load_txt_as_docs


def setup_logger(log_path: str) -> logging.Logger:
    logger = logging.getLogger("ingest")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    if log_path:
        log_dir = os.path.dirname(log_path) or "."
        os.makedirs(log_dir, exist_ok=True)

        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


def log_block_header(logger: logging.Logger) -> None:
    logger.info("=" * 80)


def log_block_body(logger: logging.Logger, text: str) -> None:
    file_handler = None
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler):
            file_handler = h
            break

    if file_handler is None:
        for line in text.splitlines():
            logger.info("%s", line)
        return

    for line in text.splitlines():
        file_handler.stream.write(line + "\n")
    file_handler.stream.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default=None, help="문서 폴더 (기본: .env DATA_DIR)")
    parser.add_argument("--collection", default="patents", help="Qdrant collection name")
    parser.add_argument("--qdrant_url", default="http://localhost:6333", help="Qdrant REST URL")
    parser.add_argument("--log_path", default="log/log_ingest.log", help="디버그 출력 로그 파일 경로")
    args = parser.parse_args()

    logger = setup_logger(args.log_path)

    cfg = configure_llamaindex()
    data_dir = args.data_dir or cfg.data_dir
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"data_dir not found: {data_dir}")

    # Qdrant 연결
    client = QdrantClient(url=args.qdrant_url)
    vector_store = QdrantVectorStore(client=client, collection_name=args.collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 파일 목록
    txt_paths = sorted(glob.glob(os.path.join(data_dir, "**", "*.txt"), recursive=True))
    if not txt_paths:
        raise ValueError(f"no txt files under {data_dir}")

    total_files = 0
    total_docs = 0

    for txt_path in txt_paths:
        file_docs = load_txt_as_docs(txt_path)
        if not file_docs:
            continue

        total_files += 1
        total_docs += len(file_docs)

        for d in file_docs:
            log_block_header(logger)
            log_block_body(logger, f"[DOC] metadata={d.metadata}")
            log_block_body(logger, d.text[:500])

        VectorStoreIndex.from_documents(
            file_docs,
            storage_context=storage_context,
            show_progress=True,
        )

    print(
        f"[OK] Indexed streaming: files={total_files}, docs={total_docs} "
        f"-> Qdrant collection='{args.collection}' ({args.qdrant_url})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
