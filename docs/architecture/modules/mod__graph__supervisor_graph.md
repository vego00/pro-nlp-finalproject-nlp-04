---
title: "src/graph/supervisor_graph.py"
tags:
  - code
  - layer/langgraph
---

# `src/graph/supervisor_graph.py`

- **소속 계층 태그**: `#layer/langgraph`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__supervisor]], [[mod__graph__idea_graph]], [[mod__graph__plan_graph]], [[mod__graph__research_graph]], [[mod__state__base]]



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/graph/supervisor_graph.py`)

```python
from langgraph.graph import StateGraph, END
from state.base import GlobalState
from graph.idea_graph import idea_subgraph
from graph.plan_graph import plan_subgraph
# =====================================================
# [Research 연동] run_research_for_plan 래퍼 함수 사용
# 
# research_subgraph는 ResearchState를 기대하지만,
# run_research_for_plan은 GlobalState를 받아서 내부적으로 변환 후
# research_subgraph를 호출하고 결과를 GlobalState.research에 저장
# =====================================================
from graph.research_graph import run_research_for_plan
from agents.supervisor import supervisor_node, ask_user, supervisor_router, prepare_idea_structuring, edit


# 노드 설정
supervisor_graph = StateGraph(GlobalState)
supervisor_graph.add_node("supervisor", supervisor_node)
supervisor_graph.add_node("ask_user", ask_user)
supervisor_graph.add_node("prepare_idea_structuring", prepare_idea_structuring)
supervisor_graph.add_node("idea_phase", idea_subgraph)
supervisor_graph.add_node("plan_phase", plan_subgraph)
supervisor_graph.add_node("edit_phase", edit)
# Research 노드: GlobalState <-> ResearchState 변환을 담당하는 래퍼 사용
supervisor_graph.add_node("research_phase", run_research_for_plan)
supervisor_graph.set_entry_point("supervisor")

# 엣지 설정
supervisor_graph.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "ASK_USER": "ask_user",
        "RUN_IDEA_STRUCTURING": "prepare_idea_structuring",
        "RUN_PLANNING": "plan_phase",
        "RUN_EDIT": "edit_phase",
        "RUN_RESEARCH": "research_phase",
        "supervisor_node": "supervisor",
        "Refresh": END,
    }
)
supervisor_graph.add_edge("ask_user", END)
supervisor_graph.add_edge("prepare_idea_structuring", "idea_phase")
supervisor_graph.add_edge("idea_phase", "supervisor")
supervisor_graph.add_edge("plan_phase", "supervisor")
supervisor_graph.add_edge("edit_phase", "supervisor")
supervisor_graph.add_edge("research_phase", "supervisor")

# 컴파일
supervisor_app = supervisor_graph.compile()
```
