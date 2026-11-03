---
title: "src/graph/edit_graph.py"
tags:
  - code
  - layer/langgraph
---

# `src/graph/edit_graph.py`

- **소속 계층 태그**: `#layer/langgraph`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__edit]], [[mod__state__edit]]

> Edit Pipeline Graph

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def build_edit_pipeline()`

## 소스 코드 미리보기 (`src/graph/edit_graph.py`)

```python
"""
Edit Pipeline Graph
"""
import sys
import os

# Add src to path if running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langgraph.graph import StateGraph, END
from state.edit import EditInternalState
from agents.edit import regenerate_node, evaluate_node, route_evaluation

def build_edit_pipeline():
    """
    단일 섹션 재생성 파이프라인 (Self-Correction Loop 포함)
    Node: regenerate -> evaluate -> (loop) or end
    """
    workflow = StateGraph(EditInternalState)
    
    # Node 추가
    workflow.add_node("regenerate", regenerate_node)
    workflow.add_node("evaluate", evaluate_node)
    
    # Flow 정의
    workflow.set_entry_point("regenerate")
    workflow.add_edge("regenerate", "evaluate")
    workflow.add_conditional_edges(
        "evaluate",
        route_evaluation,
        {
            "regenerate": "regenerate",
            "end": END
        }
    )
    
    return workflow.compile()

# Singleton Instance
edit_subgraph = build_edit_pipeline()

# Alias for consistency with other graphs
create_edit_graph = build_edit_pipeline

if __name__ == "__main__":
    # Full test script: exp/test_edit_graph.py
    print(">>> Edit Graph loaded successfully.")
    print(f">>> Nodes: {edit_subgraph.get_graph().nodes}")
```
