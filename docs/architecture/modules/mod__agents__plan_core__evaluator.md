---
title: "src/agents/plan_core/evaluator.py"
tags:
  - code
  - layer/agent
---

# `src/agents/plan_core/evaluator.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__plan_core__schemas]], [[mod__models__llm]], [[mod__prompts__plan_prompts]]

> Plan Confidence Evaluator - 2-Stage Confidence System

## 정의된 클래스 / 상태 스키마
- `ResearchNeedScore`

## 정의된 함수 / 노드
- `def evaluate_research_need(blueprint_item, planning_style, rationale)`
- `def evaluate_groundedness(content, evidence_store)`

## 소스 코드 미리보기 (`src/agents/plan_core/evaluator.py`)

```python
"""
Plan Confidence Evaluator - 2-Stage Confidence System

Stage 1: Pre-write ResearchNeedScore
- 섹션 작성 전 리서치 필요 여부 결정

Stage 2: Post-write GroundednessScore  
- 작성 후 주장-근거 정합성 검증
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

from agents.plan_core.schemas import BlueprintItem
from models.llm import get_llm
from prompts.plan_prompts import RESEARCH_NEED_PROMPT


# ===========================
# Pydantic Schemas
# ===========================

class ResearchNeedScore(BaseModel):
    """Pre-write: 리서치 필요도 평가 결과"""
    score: float = Field(..., ge=0.0, le=1.0, description="리서치 필요도 (높을수록 필요)")
    needs_research: bool = Field(..., description="리서치 필요 여부")
    research_goal: str = Field(default="", description="리서치 목적 및 필요 정보 (Context & Intent)")
    reasoning: str = Field(default="", description="평가 근거 및 공백 분석")
    
    # Optional fields for backward compatibility or detailed analysis
    fact_requirement: Optional[float] = Field(None, description="(Deprecated) 팩트 요구 수준")
    external_dependency: Optional[float] = Field(None, description="(Deprecated) 외부 의존도")
    hallucination_risk: Optional[float] = Field(None, description="(Deprecated) 할루시네이션 위험")


# ===========================
# Stage 1: Pre-write ResearchNeedScore
# ===========================




def evaluate_research_need(
    blueprint_item: BlueprintItem,
    planning_style: str = "Business",
    rationale: str = ""
) -> ResearchNeedScore:
    """
    섹션 작성 전 리서치 필요도 평가 (Pre-write, LLM 기반)
    
    Args:
        blueprint_item: 평가할 BlueprintItem
        planning_style: 기획 스타일
        rationale: 기획 의도
    
    Returns:
        ResearchNeedScore: 리서치 필요도 점수
    """
    chat = get_llm(max_tokens=2048, reasoning_effort="low")
    
    # [Fix] with_structured_output 대신 JsonOutputParser 사용 (호환성/파싱 개선)
    from langchain_core.output_parsers import JsonOutputParser
    # from langchain_core.prompts import PromptTemplate # 이미 ChatPromptTemplate을 사용하거나, 문자열 포맷팅 사용 중
    
    parser = JsonOutputParser(pydantic_object=ResearchNeedScore)
    
    # 프롬프트에 포맷 지침 추가 (Parser가 제공하는 지침 활용 가능하지만, 현재 프롬프트가 강력함)
    formatted_prompt = RESEARCH_NEED_PROMPT.format(
        planning_style=planning_style or "Business",
        rationale=rationale or "정보 없음",
        title=blueprint_item.title,
        guideline=blueprint_item.guideline or "없음"
    )
    
    import json
    import re

    max_retries = 3
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            # Chain 실행
            response = chat.invoke(formatted_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # [Fix] content가 리스트인 경우 처리 (dict인 경우 'text' 키 추출)
            if isinstance(content, list):
                extracted = []
                for part in content:
```
