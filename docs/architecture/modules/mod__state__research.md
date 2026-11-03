---
title: "src/state/research.py"
tags:
  - code
  - layer/state
---

# `src/state/research.py`

- **소속 계층 태그**: `#layer/state`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: 없음



## 정의된 클래스 / 상태 스키마
- `SearchQueries`
- `SearchItem`
- `SearchOutput`
- `ExtractedItem`
- `ResearchState`

## 정의된 함수 / 노드
- `def merge_search_results(old_results, new_results)`

## 소스 코드 미리보기 (`src/state/research.py`)

```python
from typing import List, Literal, Optional, Annotated
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

class SearchQueries(BaseModel):
    queries: List[str] = Field(
        default_factory=list,
        description="검색 엔진용으로 최적화된 3~6개의 검색 쿼리 리스트"
    )

class SearchItem(BaseModel):
    query: str = Field(description="페이지를 검색한 쿼리")
    title: str = Field(description="검색된 페이지의 제목")
    url: str = Field(description="원본 웹 페이지 링크")
    snippet: str = Field(description="검색 결과 얻어진 페이지 소개 또는 짧은 내용")
    content: Optional[str] = Field(description="검색 결과 얻어진 페이지 전체 내용", default=None)
    processing_type: Literal["web", "file", "skip"] = Field(default="skip")
    is_indexed: bool = Field(default=False)
    is_stale: bool = Field(default=False)
    last_scraped_at: Optional[datetime] = None # 페이지 재방문 주기
    page_hash: Optional[str] = Field(description="검색된 페이지의 변경 여부 확인을 위한 해시", default=None)

class SearchOutput(BaseModel):
    query: str
    results: List[SearchItem]

class ExtractedItem(BaseModel):
    item_type: Literal["chunk", "snippet"] = Field(description="해당 아이템의 유형", default="snippet")
    title: str = Field(description="검색된 페이지의 제목")
    url: str = Field(description="원본 웹 페이지 링크")
    content: str = Field(description="해당 청크 또는 스니펫 전체 내용", default="")
    score: float = Field(description="아이템의 쿼리에 대한 최종 유사도 Score", default=0.0)

def merge_search_results(old_results: List[SearchItem], new_results: List[SearchItem]) -> List[SearchItem]:
    """
    두 노드에서 반환된 search_results를 URL 기준으로 합치는 리듀서.
    내용이 채워진(scraped) 데이터를 우선시합니다.
    """
    # URL을 키로 하는 딕셔너리로 변환하여 중복 병합
    merged = {item.url: item for item in old_results}
    
    for new_item in new_results:
        # 이미 존재하고, 기존 데이터가 'skip'이 아니며 내용이 있다면 유지
        # 새로운 데이터가 'web'이나 'file' 처리를 거쳐 내용이 채워졌다면 업데이트
        if new_item.url not in merged or new_item.processing_type != "skip":
            merged[new_item.url] = new_item
            
    return list(merged.values())

class ResearchState(BaseModel):
    is_analysis_need: bool = Field(default=True)
    question: str = Field(default="")
    search_queries: List[str] = Field(default_factory=list)
    search_results: List[SearchItem] | List[ExtractedItem] = Field(default_factory=list)
    analysis_result: str = Field(default="")
```
