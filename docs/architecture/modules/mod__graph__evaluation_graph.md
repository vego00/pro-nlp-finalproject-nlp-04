---
title: "src/graph/evaluation_graph.py"
tags:
  - code
  - layer/langgraph
---

# `src/graph/evaluation_graph.py`

- **소속 계층 태그**: `#layer/langgraph`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__evaluation]], [[mod__state__base]]



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/graph/evaluation_graph.py`)

```python
from langgraph.graph import END, StateGraph

from agents.evaluation import evaluation_node
from state.base import GlobalState

evaluation_graph = StateGraph(GlobalState)
evaluation_graph.add_node("evaluate_document", evaluation_node)
evaluation_graph.set_entry_point("evaluate_document")
evaluation_graph.add_edge("evaluate_document", END)
evaluation_subgraph = evaluation_graph.compile()
```
