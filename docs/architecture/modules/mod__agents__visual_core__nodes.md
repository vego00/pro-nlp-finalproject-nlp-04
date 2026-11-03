---
title: "src/agents/visual_core/nodes.py"
tags:
  - code
  - layer/agent
---

# `src/agents/visual_core/nodes.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__plan_core__logger]], [[mod__agents__visual_core__generator]], [[mod__agents__visual_core__router]], [[mod__agents__visual_core__schemas]], [[mod__agents__visual_core__validator]], [[mod__state__visual]]

> Visual Agent 전용 노드 함수들

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def parse_request_node(state)`
- `def visual_decide_node(state)`
- `def visual_generate_node(state)`
- `def visual_validate_node(state)`
- `def visual_finalize_node(state)`
- `def route_visual_validation(state)`

## 소스 코드 미리보기 (`src/agents/visual_core/nodes.py`)

```python
"""
Visual Agent 전용 노드 함수들
"""
from typing import Dict, Any, List
from state.visual import VisualInternalState
from agents.plan_core.logger import get_logger, LogLevel
from agents.visual_core.schemas import Decision, VisualMeta, VisualArtifact
from agents.visual_core.router import decide_node, generate_visual_meta
from agents.visual_core.generator import render_table, render_diagram, render_chart, image_search, image_gen, create_visual_artifact
from agents.visual_core.validator import validate_and_decide_retry

# ===========================
# 시각화 처리 노드 (VisualInternalState 기반)
# ===========================

def parse_request_node(state: VisualInternalState) -> VisualInternalState:
    """
    [진입점] 요청된 visual_request를 분석하거나, context를 정리 (Placeholder)
    """
    print(f"[VisualAgent] 요청 수신: {state['visual_request']}")
    return state

def visual_decide_node(state: VisualInternalState) -> VisualInternalState:
    logger = get_logger()
    
    # Visual Core 로직은 기존 함수 재사용 (입력 포맷 매핑 필요)
    # 기존 decide_node는 dict를 입력받으므로 변환
    temp_state = {
        "section_id": state["target_section_id"],
        "section_title": "", # 필요시 추가
        "section_text": state["context_text"],
        "retry_count": state["retry_count"]
    }
    
    result_state = decide_node(temp_state)
    result_state = generate_visual_meta(result_state)
    
    # 결정 결과 로깅
    logger.log_visual_decision(state["target_section_id"], result_state.get("decision", {}))
    
    # 중요: Decision 정보를 state에 저장 (추후 참조를 위해 visual_type 매핑)
    decision = Decision(**result_state.get("decision", {}))
    
    visual_type = ""
    if decision.needs_chart: visual_type = "chart"
    elif decision.needs_diagram: visual_type = "diagram"
    elif decision.needs_table: visual_type = "table"
    elif decision.needs_image_search: visual_type = "image_search"
    elif decision.needs_image_gen: visual_type = "image_gen"
    
    
    state["visual_type"] = visual_type
    state["visual_meta"] = result_state.get("visual_meta", {})
    
    return state


def visual_generate_node(state: VisualInternalState) -> VisualInternalState:
    logger = get_logger()
    
    # 매핑용 임시 State
    temp_state = {
        "section_id": state["target_section_id"],
        "section_text": state["context_text"],
        "decision": {
            "needs_chart": state["visual_type"] == "chart",
            "needs_diagram": state["visual_type"] == "diagram",
            "needs_table": state["visual_type"] == "table",
            "needs_image_search": state["visual_type"] == "image_search",
            "needs_image_gen": state["visual_type"] == "image_gen"
        },
        "visual_meta": state.get("visual_meta", {})
    }
    
    # Generator 호출 (기존 함수 재사용)
    # 주의: Generator들이 'visual_meta'를 채워서 반환함
    try:
        vt = state["visual_type"]
        if vt == "chart":
            temp_state = render_chart(temp_state)
        elif vt == "diagram":
            temp_state = render_diagram(temp_state)
        elif vt == "table":
            temp_state = render_table(temp_state)
        elif vt == "image_search":
            temp_state = image_search(temp_state)
        elif vt == "image_gen":
            temp_state = image_gen(temp_state)
            
    except Exception as e:
```
