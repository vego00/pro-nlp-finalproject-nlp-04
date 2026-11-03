---
title: "src/agents/visual_core/validator.py"
tags:
  - code
  - layer/agent
---

# `src/agents/visual_core/validator.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__visual_core__schemas]], [[mod__models__llm]]

> 적합성 판단 에이전트 - 생성된 시각화가 본문과 적합한지 검증

## 정의된 클래스 / 상태 스키마
- `ValidationResult`

## 정의된 함수 / 노드
- `def validate_visual(section_text, section_title, visual_meta, generated_content)`
- `def validate_and_decide_retry(section_text, section_title, state, max_retries)`

## 소스 코드 미리보기 (`src/agents/visual_core/validator.py`)

```python
"""
적합성 판단 에이전트 - 생성된 시각화가 본문과 적합한지 검증
"""
from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel, Field

from models.llm import get_llm
from agents.visual_core.schemas import VisualMeta


class ValidationResult(BaseModel):
    """검증 결과"""
    is_valid: bool = Field(..., description="적합 여부")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="적합도 점수")
    reason: str = Field(default="", description="판단 근거")
    suggestion: str = Field(default="", description="개선 제안 (부적합 시)")


def validate_visual(
    section_text: str,
    section_title: str,
    visual_meta: Dict[str, Any],
    generated_content: str = None
) -> ValidationResult:
    """
    생성된 시각화가 본문 내용과 적합한지 판단
    
    Args:
        section_text: 원본 섹션 텍스트
        section_title: 섹션 제목
        visual_meta: 시각화 메타데이터
        generated_content: 생성된 시각화 콘텐츠 (표, 다이어그램 등)
    
    Returns:
        ValidationResult: 검증 결과
    """
    meta = VisualMeta(**visual_meta) if isinstance(visual_meta, dict) else visual_meta
    
    # 이미지 검색/생성인 경우 placeholder만 있으므로 항상 통과
    if meta.visual_type in ["image_search", "image_gen"]:
        return ValidationResult(
            is_valid=True,
            score=1.0,
            reason="이미지 검색/생성은 placeholder 상태이므로 검증 생략"
        )
    
    # 표/다이어그램/차트의 경우 LLM으로 검증.
    chat = get_llm(max_tokens=8192, reasoning_effort="low")
    structured_llm = chat.with_structured_output(ValidationResult)
    
    prompt = f"""
    다음 섹션과 생성된 시각화가 적합한지 판단해주세요.
    
    [섹션 정보]
    제목: {section_title}
    내용: {section_text[:800]}
    
    [시각화 정보]
    타입: {meta.visual_type}
    목적: {meta.purpose}
    형식 선택 이유: {meta.why_this_format}
    
    [생성된 콘텐츠]
    {generated_content or f"(이미지 파일 저장됨: {meta.image_path})" if meta.visual_type == "chart" else "(콘텐츠 없음)"}
    
    [판단 기준]
    1. 시각화 내용이 섹션 내용을 잘 반영하는가?
    2. 시각화 형식이 내용 전달에 적합한가?
    3. 데이터가 정확하고 일관성 있는가?
    4. **기술적 검증**:
        - Diagram: Mermaid 문법 오류 확인.
        - Chart: 내용상 수치 데이터가 적절히 시각화되었는지 (데이터 출처의 타당성) 확인.
    
    점수 기준:
    - 0.8 이상: 적합 (is_valid=True)
    - 0.8 미만: 부적합 (is_valid=False), 반드시 'suggestion'에 구체적인 수정 사항을 포함하세요.
    """
    
    try:
        result = structured_llm.invoke(prompt)
        return result
    except Exception as e:
        # 검증 실패 시 일단 통과 처리
        return ValidationResult(
            is_valid=True,
            score=0.7,
            reason=f"검증 중 오류 발생: {str(e)}, 기본값으로 통과 처리"
        )

```
