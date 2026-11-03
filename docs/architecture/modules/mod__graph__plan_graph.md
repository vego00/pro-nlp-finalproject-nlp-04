---
title: "src/graph/plan_graph.py"
tags:
  - code
  - layer/langgraph
---

# `src/graph/plan_graph.py`

- **소속 계층 태그**: `#layer/langgraph`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__plan]], [[mod__state__base]]

> Plan 서브그래프 - Blueprint 기반 기획서 생성 (Global Wrapper Graph)

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/graph/plan_graph.py`)

```python
"""
Plan 서브그래프 - Blueprint 기반 기획서 생성 (Global Wrapper Graph)
"""
from langgraph.graph import StateGraph, END
import sys
import os

# Add src to path if running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from state.base import GlobalState
from agents.plan import plan_generate, plan_evaluate, plan_eval_router

# 노드 설정
plan_graph = StateGraph(GlobalState)
plan_graph.add_node("generate", plan_generate)
plan_graph.add_node("evaluate", plan_evaluate)
plan_graph.set_entry_point("generate")

# 엣지 설정
plan_graph.add_edge("generate", "evaluate")
plan_graph.add_conditional_edges(
    "evaluate",
    plan_eval_router,
    {
        "pass": END,
        "retry": "generate"
    }
)

plan_subgraph = plan_graph.compile()


# ===========================
# Test Block
# ===========================
if __name__ == "__main__":
    from pprint import pprint
    import json
    from pathlib import Path
    
    # Load Mock Data from sample_blueprint.json
    project_root = Path(__file__).parent.parent.parent
    sample_file = project_root / "sample_blueprint.json"
    
    with open(sample_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Update: Construct state with 'plan' key
    mock_state: GlobalState = {
        "idea": {
            "planning_style": data.get("planning_style", "General"),
            "rationale": data.get("rationale", ""),
            "toc": data.get("toc", [])
        },
        "plan": {
            "blueprint": data.get("blueprint", [])
        },
        "current_task": "plan"
    }
    print(f">>> Loaded mock data from {sample_file}")

    print("\n>>> Testing Plan Wrapper Graph (Real LLM Calls)...")
    final_state = plan_subgraph.invoke(mock_state)
    
    # Check 'plan' state for output
    plan_output = final_state.get("plan", {})
    if plan_output and plan_output.get("sections"):
        print(">>> SUCCESS: Plan Output Generated")
        print(f"Generated {len(plan_output['sections'])} sections.")
    else:
        print(">>> FAIL: Plan Output Missing")
```
