---
title: "src/state/visual.py"
tags:
  - code
  - layer/state
---

# `src/state/visual.py`

- **소속 계층 태그**: `#layer/state`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__state__base]]

> Visual Agent 전용 내부 상태 정의

## 정의된 클래스 / 상태 스키마
- `VisualInternalState`

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/state/visual.py`)

```python
"""
Visual Agent 전용 내부 상태 정의
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from state.base import GlobalState

class VisualInternalState(GlobalState):
    """
    시각화 생성 파이프라인 상태
    
    [입력]
    - target_section_id: 시각화 대상 섹션 ID
    - visual_request: 사용자의 시각화 요청 (Optional)
    - context_text: 시각화할 본문 텍스트
    
    [출력]
    - visual_type: 결정된 시각화 유형
    - visual_meta: 시각화 메타데이터
    - code/html: 생성된 코드 및 결과값
    """
    
    # --- Input Fields ---
    target_section_id: Annotated[str, "시각화 대상 섹션 ID"]
    visual_request: Annotated[str, "시각화 요청 사항 (예: '표로 정리해줘')"]
    context_text: Annotated[str, "시각화 생성을 위한 참고 텍스트"]
    
    # --- Output Steps ---
    
    # 1. Decision & Meta
    visual_type: Annotated[str, "결정된 시각화 유형 (Table/Chart/Diagram)"]
    visual_meta: Annotated[Dict[str, Any], "시각화 메타데이터 (Purpose, Why, etc.)"]
    
    # 2. Generation
    code: Annotated[str, "생성된 코드 (Python/Mermaid)"]
    html: Annotated[str, "렌더링된 HTML 또는 결과물"]
    
    # 3. Validation
    validation_results: Annotated[Dict[str, Any], "검증 결과"]
    
    # --- Internal Logic ---
    retry_count: Annotated[int, "재시도 횟수"]
```
