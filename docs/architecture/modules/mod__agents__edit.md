---
title: "src/agents/edit.py"
tags:
  - code
  - layer/agent
---

# `src/agents/edit.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__edit_core__evaluation]], [[mod__agents__edit_core__nodes]]

> Edit Agent Entry Point

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/agents/edit.py`)

```python
"""Edit Agent Entry Point"""
from agents.edit_core.nodes import regenerate_node
from agents.edit_core.evaluation import evaluate_node, route_evaluation

__all__ = ["regenerate_node", "evaluate_node", "route_evaluation"]
```
