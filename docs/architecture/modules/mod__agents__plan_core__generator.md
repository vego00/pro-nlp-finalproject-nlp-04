---
title: "src/agents/plan_core/generator.py"
tags:
  - code
  - layer/agent
---

# `src/agents/plan_core/generator.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__plan_core__schemas]], [[mod__agents__visual_core__schemas]], [[mod__models__llm]], [[mod__prompts__edit_prompts]], [[mod__prompts__plan_prompts]]

> 기획서 생성 시스템 - 핵심 모듈

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def generate_section_from_blueprint(structured_input, blueprint_item, section_index, previous_sections, evidence, evidence_for_record)`
- `def compose_plan_markdown(plan, visual_artifacts)`
- `def format_plan_header(plan)`
- `def format_plan_toc(plan)`
- `def format_section_content(section, visual)`
- `def _format_visual_block(visual)`
- `def generate_partial_edit(instruction, target_text, prefix_text, suffix_text, granularity)`

## 소스 코드 미리보기 (`src/agents/plan_core/generator.py`)

```python
"""
기획서 생성 시스템 - 핵심 모듈
"""
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from models.llm import get_llm
from agents.plan_core.schemas import (
    StructuredIdea,
    TableOfContents,
    TableOfContentsItem,
    PlanSection,
    GeneratedPlan,
    BlueprintItem,
    StructuredInput,
)
from prompts.plan_prompts import SECTION_GENERATION_SYSTEM_PROMPT, SECTION_GENERATION_USER_PROMPT
from prompts.edit_prompts import PARTIAL_EDIT_SYSTEM_PROMPT, PARTIAL_EDIT_USER_PROMPT


# ===========================
# Blueprint 기반 생성 함수
# ===========================

def generate_section_from_blueprint(
    structured_input: StructuredInput,
    blueprint_item: BlueprintItem,
    section_index: int,
    previous_sections: List[PlanSection] = None,
    evidence: List[str] = None,
    evidence_for_record: List[str] = None
) -> PlanSection:
    """
    Blueprint 항목을 기반으로 섹션을 생성합니다.
    - guideline + content(참고 컨텍스트) + 이전 섹션 컨텍스트로 LLM 생성
    - evidence가 있으면 프롬프트에 포함하여 팩트 기반 작성 유도
    """
    section_number = str(section_index + 1)
    
    # content가 없으면 LLM으로 생성
    previous_sections = previous_sections or []
    evidence = evidence or []
    
    # 전체 목차
    toc_text = "\n".join([f"{i+1}. {title}" for i, title in enumerate(structured_input.toc)])
    
    guideline = blueprint_item.guideline or ""

    # 시스템 프롬프트 생성
    system_prompt = SECTION_GENERATION_SYSTEM_PROMPT.format(
        planning_style=structured_input.planning_style,
        rationale=structured_input.rationale,
        toc_text=toc_text,
        guideline=guideline
    )

    context_hint = blueprint_item.content or ""
    
    # 유저 프롬프트 생성
    user_prompt = SECTION_GENERATION_USER_PROMPT.format(
        title=blueprint_item.title,
        user_content=context_hint,
        evidence= evidence
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # LLM 호출
    chat = get_llm(max_tokens=8192, reasoning_effort="medium")
    response = chat.invoke(messages)
    
    # 후처리: LLM이 섹션 제목을 포함했을 경우 제거
    content = response.content.strip()
    lines = content.split('\n')
    
    # 첫 몇 줄에서 섹션 제목과 동일하거나 유사한 제목 제거
    title_keywords = blueprint_item.title.lower().replace(' ', '')
    cleaned_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 제목 줄인지 확인
        if stripped.startswith('#'):
            # 제목 텍스트 추출
            title_text = stripped.lstrip('#').strip().lower().replace(' ', '')
            # 섹션 번호나 제목과 유사한 경우 제거
            if (title_keywords in title_text or 
```
