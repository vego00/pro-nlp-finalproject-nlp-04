---
title: "src/agents/research.py"
tags:
  - code
  - layer/agent
---

# `src/agents/research.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: 없음



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/agents/research.py`)

```python
﻿"""Free web research with local embeddings and persistent Qdrant retrieval."""
import hashlib
import logging
import uuid
from datetime import datetime, timezone, timedelta
from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate
from qdrant_client import QdrantClient, models
from config import config as settings
from models.llm import get_llm
from models.embeddings import embed_documents, embed_query, embedding_dimension
from state.research import ResearchState, SearchQueries, SearchItem, ExtractedItem
from prompts.research_prompts import RESEARCH_ANALYSIS_PROMPT, RESEARCH_QUERY_GEN_PROMPT

logger = logging.getLogger(__name__)
# A separate collection prevents mixing vectors from different embedding models.
COLLECTION_NAME = "web-" + hashlib.sha256(settings.EMBEDDING_MODEL.encode()).hexdigest()[:12]


@lru_cache(maxsize=1)
def get_store():
    client = (QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
              if settings.QDRANT_URL else QdrantClient(path=str(settings.QDRANT_PATH)))
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            COLLECTION_NAME,
            vectors_config={"text-dense": models.VectorParams(
                size=embedding_dimension(), distance=models.Distance.COSINE)},
            sparse_vectors_config={"text-sparse": models.SparseVectorParams()})
    return client


def research_generate(state):
    return state


def research_evaluate(state):
    return state


def research_eval_router(state):
    return "pass"


def generate_queries(state: ResearchState):
    prompt = ChatPromptTemplate.from_messages([
        ("system", RESEARCH_QUERY_GEN_PROMPT), ("human", "{question}")])
    chain = prompt | get_llm(temperature=0.1).with_structured_output(SearchQueries)
    result = chain.invoke({"question": state.question})
    queries = [q.strip() for q in result.queries if q.strip()]
    return {"search_queries": (queries or [state.question])[:settings.SEARCH_MAX_QUERIES]}


def search_with_tavily(state: ResearchState):
    """Historical node name; provider is selected in config.py."""
    results = {}
    failures = []
    for query in state.search_queries[:settings.SEARCH_MAX_QUERIES]:
        try:
            if settings.SEARCH_PROVIDER == "tavily":
                if not settings.TAVILY_API_KEY:
                    raise ValueError("TAVILY_API_KEY가 필요합니다.")
                from langchain_tavily import TavilySearch
                output = TavilySearch(max_results=settings.SEARCH_MAX_RESULTS,
                    search_depth="basic", include_raw_content=False,
                    tavily_api_key=settings.TAVILY_API_KEY).invoke({"query": query})
                rows = output.get("results", []) if isinstance(output, dict) else []
            elif settings.SEARCH_PROVIDER == "duckduckgo":
                from ddgs import DDGS
                rows = DDGS(timeout=15).text(query, max_results=settings.SEARCH_MAX_RESULTS,
                                             backend="duckduckgo")
            else:
                raise ValueError(f"지원하지 않는 SEARCH_PROVIDER: {settings.SEARCH_PROVIDER}")
            for row in rows:
                url = row.get("url") or row.get("href", "")
                if not url.startswith(("https://", "http://")):
                    continue
                snippet = (row.get("content") or row.get("body") or "")[:1800]
                results[url] = SearchItem(query=query, title=row.get("title", url),
                    url=url, snippet=snippet, content=snippet)
        except Exception as exc:
            logger.warning("Search failed for %s: %s", query, exc)
            failures.append(type(exc).__name__)
    if not results:
        raise RuntimeError("웹 검색 결과가 없습니다. 네트워크 또는 검색 제공자 설정을 확인하세요."
                           + (" (" + ", ".join(failures) + ")" if failures else ""))
    return {"search_results": list(results.values())}


```
