---
title: "src/agents/visual.py"
tags:
  - code
  - layer/agent
---

# `src/agents/visual.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__visual_core__nodes]]

> Visual Agent Entry Point

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/agents/visual.py`)

```python
"""Visual Agent Entry Point"""
from agents.visual_core.nodes import (
    visual_decide_node,
    visual_generate_node,
    visual_validate_node,
    visual_finalize_node,
    route_visual_validation
)

__all__ = [
    "visual_decide_node",
    "visual_generate_node",
    "visual_validate_node",
    "visual_finalize_node",
    "route_visual_validation"
]
```
