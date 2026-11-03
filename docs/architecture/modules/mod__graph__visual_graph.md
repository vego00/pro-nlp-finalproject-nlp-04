---
title: "src/graph/visual_graph.py"
tags:
  - code
  - layer/langgraph
---

# `src/graph/visual_graph.py`

- **소속 계층 태그**: `#layer/langgraph`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__visual]], [[mod__state__visual]]

> Visual Agent Subgraph - 시각화 생성 및 수정 전담

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def build_visual_pipeline()`

## 소스 코드 미리보기 (`src/graph/visual_graph.py`)

```python
"""
Visual Agent Subgraph - 시각화 생성 및 수정 전담
"""
from langgraph.graph import StateGraph, END
import sys
import os

# Add src to path if running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from state.visual import VisualInternalState
# Visual Nodes (Refactored Location)
from agents.visual import (
    visual_decide_node,
    visual_generate_node,
    visual_validate_node,
    visual_finalize_node,
    route_visual_validation
)

def build_visual_pipeline():
    """
    VisualInternalState를 사용하는 StateGraph 정의
    """
    g = StateGraph(VisualInternalState)
    
    # 노드 추가
    g.add_node("visual_decide", visual_decide_node)
    g.add_node("visual_generate", visual_generate_node)
    g.add_node("visual_validate", visual_validate_node)
    g.add_node("visual_finalize", visual_finalize_node)
    
    # 엣지 및 흐름 제어
    g.set_entry_point("visual_decide")
    
    g.add_edge("visual_decide", "visual_generate")
    g.add_edge("visual_generate", "visual_validate")
    
    g.add_conditional_edges(
        "visual_validate",
        route_visual_validation,
        {
            "visual_generate": "visual_generate",
            "visual_finalize": "visual_finalize"
        }
    )
    
    g.add_edge("visual_finalize", END)
    
    return g.compile()

visual_subgraph = build_visual_pipeline()

# Alias for consistency with other graphs
create_visual_graph = build_visual_pipeline

if __name__ == "__main__":
    # Test Block
    print(">>> Testing Visual Graph...")
    mock_state = {
        # GlobalState Fields (Mock)
        "messages": [],
        "awaiting_input": False,
        "input_request": None,
        "user_response": None,
        "current_task": "visual",
        "idea": {},
        "plan": {},
        "edit": {},
        "visual": {},
        "supervision": {},
        
        # VisualInternalState Fields
        "target_section_id": "sec-1",
        "visual_request": "매출 중가 추이를 막대 그래프로 그려줘",
        "context_text": "2023년 매출: 100억, 2024년 매출: 150억, 2025년 예상: 200억",
        "visual_type": "",
        "visual_meta": {},
        "code": "",
        "html": "",
        "validation_results": {},
        "retry_count": 0
    }
    
    try:
        final_state = visual_subgraph.invoke(mock_state)
        print(">>> Visual Generation Complete")
        print(f"Type: {final_state['visual_type']}")
        print(f"Code:\n{final_state['code']}")
    except Exception as e:
```
