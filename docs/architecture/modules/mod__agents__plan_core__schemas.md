---
title: "src/agents/plan_core/schemas.py"
tags:
  - code
  - layer/agent
---

# `src/agents/plan_core/schemas.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: 없음

> 기획서 생성 시스템용 스키마 정의

## 정의된 클래스 / 상태 스키마
- `StructuredIdea`
- `TableOfContentsItem`
- `TableOfContents`
- `PlanSection`
- `GeneratedPlan`
- `BlueprintItem`
- `StructuredInput`

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/agents/plan_core/schemas.py`)

```python
"""
기획서 생성 시스템용 스키마 정의
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class StructuredIdea(BaseModel):
    """사용자 아이디어를 구조화한 스키마"""
    title: str = Field(..., description="프로젝트/서비스 제목")
    summary: str = Field(..., description="한 줄 요약")
    problem: str = Field(..., description="해결하고자 하는 문제")
    target_users: List[str] = Field(default_factory=list, description="타겟 사용자 목록")
    core_features: List[str] = Field(default_factory=list, description="핵심 기능 목록")
    differentiators: List[str] = Field(default_factory=list, description="차별점/경쟁우위")
    business_model: Optional[str] = Field(default=None, description="수익 모델")
    tech_stack: Optional[List[str]] = Field(default=None, description="기술 스택")
    constraints: Optional[List[str]] = Field(default=None, description="제약사항")


class TableOfContentsItem(BaseModel):
    """목차 항목"""
    section_number: str = Field(..., description="섹션 번호 (예: '1', '1.1', '2')")
    title: str = Field(..., description="섹션 제목")
    guideline: Optional[str] = Field(
        default=None, 
        description="이 섹션에서 작성할 내용의 가이드라인"
    )


class TableOfContents(BaseModel):
    """전체 목차"""
    items: List[TableOfContentsItem] = Field(default_factory=list)


class PlanSection(BaseModel):
    """생성된 섹션 내용"""
    section_number: str
    title: str
    content: str = Field(..., description="마크다운 형식의 섹션 본문")
    evidence: List[str] = Field(default_factory=list, description="참고한 리서치 자료/근거")


class GeneratedPlan(BaseModel):
    """최종 생성된 기획서"""
    idea: StructuredIdea
    toc: TableOfContents
    sections: List[PlanSection] = Field(default_factory=list)
    method: str = Field(..., description="사용된 생성 방법 (blueprint)")


# ===========================
# Blueprint 기반 입력 스키마
# ===========================

class BlueprintItem(BaseModel):
    """Blueprint 개별 항목 (외부 에이전트 제공)"""
    title: str = Field(..., description="섹션 제목")
    content: Optional[str] = Field(None, description="미리 작성된 내용 (있으면 그대로 사용)")
    guideline: Optional[str] = Field(None, description="LLM 생성 시 참고할 가이드라인")
    is_required_from_user: bool = Field(False, description="사용자 입력이 필요한 항목 여부")


class StructuredInput(BaseModel):
    """외부 에이전트가 제공하는 구조화된 입력"""
    planning_style: str = Field(..., description="기획 스타일 (예: Business, Technical)")
    rationale: str = Field(..., description="해당 스타일 선택 이유")
    toc: List[str] = Field(default_factory=list, description="목차 리스트")
    blueprint: List[BlueprintItem] = Field(default_factory=list, description="섹션별 청사진")



```
