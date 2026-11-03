---
title: "src/agents/evaluation_core/metrics.py"
tags:
  - code
  - layer/agent
---

# `src/agents/evaluation_core/metrics.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__evaluation_core__schemas]]

> Validate coverage and calculate scores without asking an LLM to do arithmetic.

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def ratio(numerator, denominator)`
- `def calculate_metrics(inputs, assessment)`

## 소스 코드 미리보기 (`src/agents/evaluation_core/metrics.py`)

```python
"""Validate coverage and calculate scores without asking an LLM to do arithmetic."""
from collections import Counter

from agents.evaluation_core.schemas import Assessment, EvaluationInput


def ratio(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
        "status": "evaluated" if denominator else "not_applicable",
    }


def calculate_metrics(inputs: EvaluationInput, assessment: Assessment) -> dict:
    for name in ("requirements", "claims", "work_items", "edit_conditions",
                 "preservation_items", "visual_elements"):
        expected = {item.id for item in getattr(inputs, name)}
        actual = [item.id for item in getattr(assessment, name)]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError(f"Incomplete, duplicate or unexpected judgments: {name}")
    sources = {item.id for item in inputs.sources}
    for claim in assessment.claims:
        if not set(claim.source_ids) <= sources:
            raise ValueError(f"Unknown source for claim {claim.id}")
        if claim.category == "source_verified" and not claim.source_ids:
            raise ValueError(f"Missing source for claim {claim.id}")
        if claim.category == "input_verified" and not inputs.original_input.strip():
            raise ValueError(f"Missing original input for claim {claim.id}")
    for name in ("contradictions", "visual_omissions", "visual_wrong_connections"):
        issues = getattr(assessment, name)
        if len({issue.id for issue in issues}) != len(issues):
            raise ValueError(f"Duplicate issue IDs: {name}")
    if not inputs.visual_elements and (assessment.visual_omissions or assessment.visual_wrong_connections):
        raise ValueError("Visual issues require a visual inventory")

    def score(name, invert=False):
        judgments = getattr(assessment, name)
        count = sum(not item.passed if invert else item.passed for item in judgments)
        return ratio(count, len(getattr(inputs, name)))

    categories = Counter(claim.category for claim in assessment.claims)
    contradiction_count = len(assessment.contradictions)
    return {
        "requirement_coverage": score("requirements"),
        "claim_verification": ratio(categories["input_verified"] + categories["source_verified"], len(inputs.claims)),
        "claim_categories": {key: categories[key] for key in (
            "input_verified", "source_verified", "explicit_assumption", "unsupported")},
        "consistency": {
            "contradiction_count": contradiction_count,
            "requirement_count": len(inputs.requirements),
            "per_10_requirements": contradiction_count * 10 / len(inputs.requirements) if inputs.requirements else None,
        },
        "usability": score("work_items"),
        "edit_accuracy": score("edit_conditions"),
        "unintended_change_rate": score("preservation_items", invert=True),
        "visual_accuracy": score("visual_elements"),
        "visual_omission_count": len(assessment.visual_omissions) if inputs.visual_elements else None,
        "visual_wrong_connection_count": len(assessment.visual_wrong_connections) if inputs.visual_elements else None,
    }
```
