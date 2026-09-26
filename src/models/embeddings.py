"""Lazy CPU embedding backend. FastEmbed applies model-specific query prefixes."""
from functools import lru_cache
from config import config as settings


@lru_cache(maxsize=1)
def get_embeddings():
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=settings.EMBEDDING_MODEL,
                         cache_dir=str(settings.MODEL_CACHE_DIR), threads=4,
                         providers=["CPUExecutionProvider"])


def embed_documents(texts):
    return [vector.tolist() for vector in get_embeddings().passage_embed(texts)]


def embed_query(text):
    return next(get_embeddings().query_embed(text)).tolist()


def embedding_dimension():
    from fastembed import TextEmbedding
    for model in TextEmbedding.list_supported_models():
        if model["model"] == settings.EMBEDDING_MODEL:
            return model["dim"]
    raise ValueError(f"FastEmbed에서 지원하지 않는 임베딩 모델: {settings.EMBEDDING_MODEL}")
