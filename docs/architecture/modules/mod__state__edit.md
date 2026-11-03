---
title: "src/state/edit.py"
tags:
  - code
  - layer/state
---

# `src/state/edit.py`

- **소속 계층 태그**: `#layer/state`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__state__base]]

> Edit Pipeline Internal State

## 정의된 클래스 / 상태 스키마
- `EditInternalState`

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/state/edit.py`)

```python
"""
Edit Pipeline Internal State
"""
from __future__ import annotations
from typing import TypedDict, Dict, Any, Optional, Annotated
from state.base import GlobalState

class EditInternalState(GlobalState):
    """
    편집 파이프라인 상태
    
    [입력]
    - instruction: 유저의 수정 요청사항
    - granularity: 수정 단위 (section/paragraph/sentence)
    - edit_range_start: 부분 수정 시 범위
    - edit_range_end: 부분 수정 시 범위 (legacy)
    - idea['blueprint']: 원본 기획 데이터 참조
    
    [출력]
    - regenerated_content: 재생성된 콘텐츠
    - critique: 평가 결과
    - feedback: 개선 피드백
    """
    
    # --- Input Fields ---
    instruction: Annotated[str, "유저의 수정 요청"]
    
    # Option: Granular Edit
    granularity: Annotated[str, "수정 단위 (section/paragraph/sentence)"]
    edit_range_start: Annotated[Optional[int], "수정 시작 라인 인덱스 (Inclusive)"]
    edit_range_end: Annotated[Optional[int], "수정 끝 라인 인덱스 (Inclusive)"]

    # --- Internal Logic ---
    retry_count: Annotated[int, "재시도 횟수"]
    
    # --- Output Fields ---
    regenerated_content: Annotated[str, "재생성된 결과 (전체 텍스트 합본)"]
    critique: Annotated[Optional[str], "평가 비평"]
    feedback: Annotated[Optional[str], "재생성 피드백"]
    
    # --- Debug Info ---
    used_guideline: Annotated[Optional[str], "실제 생성에 사용된 가이드라인"]
```
