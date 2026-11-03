---
title: "src/state/plan.py"
tags:
  - code
  - layer/state
---

# `src/state/plan.py`

- **소속 계층 태그**: `#layer/state`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__state__base]]

> 기획서 파이프라인 내부 상태 정의

## 정의된 클래스 / 상태 스키마
- `PlanInternalState`

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/state/plan.py`)

```python
"""
기획서 파이프라인 내부 상태 정의
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from state.base import GlobalState


class PlanInternalState(GlobalState):
    """
    기획서 생성 파이프라인 상태
    
    [입력 (From IdeaState/Global)]
    - idea['blueprint']: 기획 청사진 (Sections, Guidelines)
    - idea['planning_style']: 기획 스타일 (Business, Technical, etc)
    
    [출력 (To GlobalState)]
    - plan['sections']: 생성된 섹션 리스트
    - plan['final_markdown']: 최종 병합된 마크다운
    - plan['output_path']: 저장된 파일 경로
    - plan['visual_artifacts']: 시각화 메타데이터
    """
    
    # --- Internal Logic State ---
    current_section_index: Annotated[int, "현재 처리 중인 섹션 인덱스 (0-based)"]
    
    # --- Temporary Processing Data ---
    sections: Annotated[List[Dict[str, Any]], "생성된 섹션 객체 리스트 (중간 저장용)"]
    visual_artifacts: Annotated[List[Dict[str, Any]], "생성된 시각화 아티팩트 리스트"]
    final_markdown: Annotated[str, "조합된 최종 마크다운"]
    output_path: Annotated[str, "파일 저장 경로"]
    plan_status: Annotated[str, "기획서 생성 상태 (IN_PROGRESS, WAITING_FOR_RESEARCH, COMPLETED)"]
    
    temp_visual_state: Annotated[Dict[str, Any], "시각화 처리를 위한 임시 데이터 (섹션 텍스트 등)"]

```
