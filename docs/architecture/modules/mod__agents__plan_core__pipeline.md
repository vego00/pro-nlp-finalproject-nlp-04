---
title: "src/agents/plan_core/pipeline.py"
tags:
  - code
  - layer/agent
---

# `src/agents/plan_core/pipeline.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__plan_core__logger]], [[mod__agents__plan_core__nodes]], [[mod__state__plan]]

> 기획서 생성 파이프라인 - Graph 정의

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def build_plan_pipeline()`
- `def invoke_plan_pipeline(initial_state)`

## 소스 코드 미리보기 (`src/agents/plan_core/pipeline.py`)

```python
"""
기획서 생성 파이프라인 - Graph 정의
"""
from langgraph.graph import StateGraph, END
from typing import Dict, Any
from state.plan import PlanInternalState
from agents.plan_core.nodes import (
    parse_input_node,
    initialize_output_node,
    generate_section_node,
    process_visual_node,
    append_section_node,
    increment_section_index_node,
    route_next_section,
    compose_output_node,
    refine_plan_node,       # [New]
    save_output_node,
)
from agents.plan_core.logger import reset_logger

def build_plan_pipeline():
    """
    PlanInternalState를 사용하는 StateGraph 정의
    """
    g = StateGraph(PlanInternalState)
    
    # 노드 추가
    g.add_node("parse_input", parse_input_node)
    g.add_node("initialize_output", initialize_output_node)
    g.add_node("generate_section", generate_section_node)
    g.add_node("process_visual", process_visual_node)
    g.add_node("append_section", append_section_node)
    g.add_node("increment_index", increment_section_index_node)
    g.add_node("compose_output", compose_output_node)
    g.add_node("refine_plan", refine_plan_node)
    g.add_node("save_output", save_output_node)
    
    # Init
    g.set_entry_point("parse_input")
    g.add_edge("parse_input", "initialize_output")
    g.add_edge("initialize_output", "generate_section")
    
    # =====================================================
    # [Research 연동] generate_section 이후 라우팅
    # =====================================================
    def route_after_section(state: PlanInternalState) -> str:
        if state.get("plan_status") == "WAITING_FOR_RESEARCH":
            return "end_for_research"
        return "process_visual"
    
    g.add_conditional_edges(
        "generate_section",
        route_after_section,
        {
            "end_for_research": END,
            "process_visual": "process_visual"
        }
    )
    
    # Visual 처리 후 섹션 저장(Append) -> 다음 인덱스
    g.add_edge("process_visual", "append_section")
    g.add_edge("append_section", "increment_index")
    
    # Route Next Section
    # [Refactor] 내부 루프 제거 -> 섹션 단위 실행 (Incremental Execution)
    # generate_section -> ... -> increment_index -> compose_output -> refine_plan -> save_output -> END
    
    # Route Next Section (Increment 후 종료)
    # 다음 섹션이 있는지 여부는 nodes.py의 increment_index에서 
    # GlobalState.plan_status를 통해 Supervisor에게 전달됨
    g.add_edge("increment_index", "compose_output")
    
    # [Refactor] Refinement는 모든 섹션이 완료(COMPLETED)된 후에만 실행
    def route_refinement(state: PlanInternalState) -> str:
        if state.get("plan_status") == "COMPLETED":
            return "refine"
        return "save"

    g.add_conditional_edges(
        "compose_output",
        route_refinement,
        {
            "refine": "refine_plan",
            "save": "save_output"
        }
    )
    
    g.add_edge("refine_plan", "save_output")
    g.add_edge("save_output", END)
    
```
