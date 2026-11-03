---
title: "src/graph/idea_graph.py"
tags:
  - code
  - layer/langgraph
---

# `src/graph/idea_graph.py`

- **소속 계층 태그**: `#layer/langgraph`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__idea]], [[mod__state__idea]]



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/graph/idea_graph.py`)

```python
import sys
import os

# 현재 파일의 부모의 부모 폴더(src)를 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, END
from state.idea import InternalState
from agents.idea import idea_router, analyzer_node, creator_node, updater_node, questioner_node, evaluator_node


# 노드 설정
idea_graph = StateGraph(InternalState)
idea_graph.add_node("analyzer", analyzer_node)
idea_graph.add_node("creator", creator_node)
idea_graph.add_node("updater", updater_node)
idea_graph.add_node("questioner", questioner_node)
idea_graph.add_node("evaluator", evaluator_node)

idea_graph.set_entry_point("analyzer")

# 엣지 설정
idea_graph.add_conditional_edges(
    "analyzer",
    idea_router,
    {
        "creator" : "creator",
        "updater" : "updater",
        "questioner": "questioner",
    }
)
idea_graph.add_edge("creator", "questioner")
idea_graph.add_edge("updater", "questioner")
idea_graph.add_edge("questioner", "evaluator")

idea_graph.add_conditional_edges(
    "evaluator",
    lambda x: x["idea"]["last_decision"],
    {
        "REJECTED": "analyzer",       
        "WAIT_FOR_USER": END,          
        "COMPLETE": END               
    }
)

# 컴파일
idea_subgraph = idea_graph.compile()
```
