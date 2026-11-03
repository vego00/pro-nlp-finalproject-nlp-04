---
title: "src/models/embeddings.py"
tags:
  - code
  - layer/model
---

# `src/models/embeddings.py`

- **소속 계층 태그**: `#layer/model`
- **상위 아키텍처 노트**: [[00-Index]], [[04-Models-and-Config]]
- **내부 모듈 의존성(Imports)**: [[mod__config__config]]

> Lazy CPU embedding backend. FastEmbed applies model-specific query prefixes.

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def get_embeddings()`
- `def embed_documents(texts)`
- `def embed_query(text)`
- `def embedding_dimension()`

## 소스 코드 미리보기 (`src/models/embeddings.py`)

```python
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
```
