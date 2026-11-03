---
title: "src/agents/visual_core/schemas.py"
tags:
  - code
  - layer/agent
---

# `src/agents/visual_core/schemas.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: 없음

> 시각화 에이전트용 스키마 정의

## 정의된 클래스 / 상태 스키마
- `TableType`
- `DiagramType`
- `ChartType`
- `Decision`
- `VisualMeta`
- `VisualArtifact`

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/agents/visual_core/schemas.py`)

```python
"""
시각화 에이전트용 스키마 정의
"""
from __future__ import annotations
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class TableType(str, Enum):
    none = "none"
    comparison = "comparison"
    roadmap = "roadmap"
    metrics = "metrics"
    taxonomy = "taxonomy"
    pricing = "pricing"
    risk = "risk"


class DiagramType(str, Enum):
    none = "none"
    architecture = "architecture"
    userflow = "userflow"
    sequence = "sequence"
    erd = "erd"
    timeline = "timeline"


class ChartType(str, Enum):
    none = "none"
    pie = "pie"
    bar = "bar"
    line = "line"
    scatter = "scatter"



class Decision(BaseModel):
    """시각화 필요성 판단 결과"""
    # 핵심 플래그
    needs_table: bool = False
    needs_diagram: bool = False
    needs_chart: bool = False
    needs_image_search: bool = False
    needs_image_gen: bool = False

    # 상세 타입
    table_type: TableType = TableType.none
    diagram_type: DiagramType = DiagramType.none
    chart_type: ChartType = ChartType.none


    # 검색/생성 힌트
    image_query: List[str] = Field(default_factory=list, description="검색 키워드(없으면 빈 배열)")
    image_gen_prompt: Optional[str] = Field(default=None, description="이미지 생성 프롬프트(생성 필요 시)")

    # 렌더링 힌트(선택)
    suggested_slots: List[str] = Field(
        default_factory=list,
        description="HTML 레이아웃 상 어느 placeholder에 들어갈지 힌트"
    )

    # 짧은 근거(디버깅/평가용)
    reason: str = Field(default="")

    # 보수적 운영을 위한 안전장치(선택)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class VisualMeta(BaseModel):
    """시각화 메타데이터 - 왜 이 시각화가 필요한지"""
    visual_type: str = Field(..., description="table, diagram, chart, image_search, image_gen")
    purpose: str = Field(..., description="시각화 목적 (예: '가격 변동 추이를 직관적으로 비교')")
    why_this_format: str = Field(..., description="왜 이 형식인지 (예: '시간에 따른 변화를 보여주기에 라인차트가 적합')")
    data_source: str = Field(default="", description="데이터 출처 설명")
    placeholder: str = Field(default="", description="임시 표기 (예: '(이미지 검색 후 삽입)')")
    content: Optional[str] = Field(default=None, description="생성된 콘텐츠 (표, 다이어그램 등)")
    image_path: Optional[str] = Field(default=None, description="로컬 저장 경로")
    image_url: Optional[str] = Field(default=None, description="외부 공개 URL (S3, drive 등)")



class VisualArtifact(BaseModel):
    """섹션에 포함될 시각화 결과물"""
    section_number: str
    meta: VisualMeta
    is_placeholder: bool = Field(default=False, description="실제 생성 vs placeholder")
```
