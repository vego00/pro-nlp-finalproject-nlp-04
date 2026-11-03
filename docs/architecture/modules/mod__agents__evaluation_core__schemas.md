---
title: "src/agents/evaluation_core/schemas.py"
tags:
  - code
  - layer/agent
---

# `src/agents/evaluation_core/schemas.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: 없음

> Explicit evaluation inventories keep metric denominators reproducible.

## 정의된 클래스 / 상태 스키마
- `StrictModel`
- `Item`
- `EvaluationInput`
- `Judgment`
- `ClaimJudgment`
- `Issue`
- `Assessment`

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/agents/evaluation_core/schemas.py`)

```python
"""Explicit evaluation inventories keep metric denominators reproducible."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Item(StrictModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class EvaluationInput(StrictModel):
    document: str = Field(min_length=1)
    original_input: str = ""
    sources: list[Item] = Field(default_factory=list)
    requirements: list[Item] = Field(default_factory=list)
    claims: list[Item] = Field(default_factory=list)
    work_items: list[Item] = Field(default_factory=list)
    original_document: str | None = None
    edit_conditions: list[Item] = Field(default_factory=list)
    preservation_items: list[Item] = Field(default_factory=list)
    visual_elements: list[Item] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_inventories(self):
        for name in ("sources", "requirements", "claims", "work_items",
                     "edit_conditions", "preservation_items", "visual_elements"):
            items = getattr(self, name)
            if len({item.id for item in items}) != len(items):
                raise ValueError(f"Duplicate IDs in {name}")
        if (self.edit_conditions or self.preservation_items) and not self.original_document:
            raise ValueError("Edit evaluation requires original_document")
        return self


class Judgment(StrictModel):
    id: str
    passed: bool
    reason: str = Field(min_length=1)
    evidence: str = Field(min_length=1, description="Exact quote/location, or missing information")


class ClaimJudgment(StrictModel):
    id: str
    category: Literal["input_verified", "source_verified", "explicit_assumption", "unsupported"]
    reason: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    source_ids: list[str] = Field(default_factory=list)


class Issue(StrictModel):
    id: str
    description: str = Field(min_length=1)
    locations: list[str] = Field(min_length=1)


class Assessment(StrictModel):
    requirements: list[Judgment]
    claims: list[ClaimJudgment]
    work_items: list[Judgment]
    edit_conditions: list[Judgment]
    preservation_items: list[Judgment]
    visual_elements: list[Judgment]
    contradictions: list[Issue]
    visual_omissions: list[Issue]
    visual_wrong_connections: list[Issue]
```
