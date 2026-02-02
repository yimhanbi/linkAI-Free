import os
from dataclasses import dataclass
from dotenv import load_dotenv

from llama_index.core import Settings

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    data_dir: str
    storage_dir: str
    chunk_size: int
    chunk_overlap: int
    retriever_top_k: int
    reranker_top_k: int
    metadata_top_k: int

    # OpenAI
    openai_api_key: str | None
    openai_llm_model: str
    openai_embed_model: str

    # Ollama
    ollama_base_url: str | None
    ollama_llm_model: str
    ollama_embed_model: str


def get_config() -> AppConfig:
    return AppConfig(
        data_dir=os.getenv("DATA_DIR", "./data"),
        storage_dir=os.getenv("STORAGE_DIR", "./storage"),
        chunk_size=int(os.getenv("CHUNK_SIZE", "1024")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "128")),
        retriever_top_k=int(os.getenv("RETRIEVER_TOP_K", "30")),
        reranker_top_k=int(os.getenv("RERANKER_TOP_K", "6")),
        metadata_top_k=int(os.getenv("METADATA_TOP_K", "6")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_llm_model=os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini"),
        openai_embed_model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL"),
        ollama_llm_model=os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:7b-instruct"),
        ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", "bge-m3"),
    )


def configure_llamaindex() -> AppConfig:
    cfg = get_config()

    
    # 모델 선택: 
    if cfg.openai_api_key:
        os.environ["OPENAI_API_KEY"] = cfg.openai_api_key
    from llama_index.llms.openai import OpenAI
        from llama_index.embeddings.openai import OpenAIEmbedding

    Settings.llm = OpenAI(model=cfg.openai_llm_model)
        Settings.embed_model = OpenAIEmbedding(model=cfg.openai_embed_model)
    else:
        from llama_index.llms.ollama import Ollama
        from llama_index.embeddings.ollama import OllamaEmbedding

        Settings.llm = Ollama(model=cfg.ollama_llm_model, base_url=cfg.ollama_base_url)
        Settings.embed_model = OllamaEmbedding(model_name=cfg.ollama_embed_model, base_url=cfg.ollama_base_url)


    ollama llm
    from llama_index.llms.ollama import Ollama
    Settings.llm = Ollama(model=cfg.ollama_llm_model, base_url=cfg.ollama_base_url)

    # ollama embedding
    from llama_index.embeddings.ollama import OllamaEmbedding
    Settings.embed_model = OllamaEmbedding(model_name=cfg.ollama_embed_model, base_url=cfg.ollama_base_url)
    

    # openai llm
    from llama_index.llms.openai import OpenAI
    Settings.llm = OpenAI(model=cfg.openai_llm_model)

    return cfg
