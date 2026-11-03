---
title: "src/agents/visual_core/generator.py"
tags:
  - code
  - layer/agent
---

# `src/agents/visual_core/generator.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__visual_core__schemas]], [[mod__models__llm]], [[mod__prompts__visual_prompts]]

> 시각화 생성 에이전트 - 표, 다이어그램, 이미지 생성/검색

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def render_table(state)`
- `def render_diagram(state)`
- `def render_chart(state)`
- `def image_search(state)`
- `def image_gen(state)`
- `def create_visual_artifact(section_number, state)`

## 소스 코드 미리보기 (`src/agents/visual_core/generator.py`)

```python
"""
시각화 생성 에이전트 - 표, 다이어그램, 이미지 생성/검색
"""
from __future__ import annotations
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from models.llm import get_llm
from agents.visual_core.schemas import Decision, VisualMeta, VisualArtifact, ChartType
from prompts.visual_prompts import TABLE_RENDER_PROMPT, DIAGRAM_RENDER_PROMPT, CHART_DATA_EXTRACTION_PROMPT


def render_table(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    표 생성 - 마크다운 테이블 생성
    """
    text = state.get("section_text", "")
    d = Decision(**state.get("decision", {}))
    visual_meta = state.get("visual_meta", {})
    
    # 이전 시도 피드백 확인
    feedback_text = ""
    v_result = state.get("validation_result")
    if v_result and not v_result.get("is_valid"):
        feedback_text = f"\n[이전 시도 피드백]: {v_result.get('suggestion')}\n위 피드백을 반영하여 다시 작성해줘."

    prompt = TABLE_RENDER_PROMPT.format(
        table_type=d.table_type.value,
        feedback_text=feedback_text,
        text=text
    )
    chat = get_llm(max_tokens=8192, reasoning_effort="low")
    response = chat.invoke(prompt)
    
    # visual_meta 업데이트
    if visual_meta:
        visual_meta["content"] = response.content
    
    state.setdefault("artifacts", {})["table"] = {
        "content": response.content,
        "type": d.table_type.value
    }
    state["visual_meta"] = visual_meta
    return state


def render_diagram(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    다이어그램 생성 - Mermaid 코드 생성
    """
    text = state.get("section_text", "")
    d = Decision(**state.get("decision", {}))
    visual_meta = state.get("visual_meta", {})
    
    # 이전 시도 피드백 확인
    feedback_text = ""
    v_result = state.get("validation_result")
    if v_result and not v_result.get("is_valid"):
        feedback_text = f"\n[이전 시도 피드백]: {v_result.get('suggestion')}\n위 피드백을 반영하여 오류를 수정해서 다시 작성해줘."

    prompt = DIAGRAM_RENDER_PROMPT.format(
        diagram_type=d.diagram_type.value,
        feedback_text=feedback_text,
        text=text
    )
    chat = get_llm(max_tokens=8192, reasoning_effort="low")
    response = chat.invoke(prompt)
    
    state.setdefault("artifacts", {})["diagram"] = {
        "content": response.content,
        "type": d.diagram_type.value
    }

    # [Fix] Mermaid 코드를 이미지로 변환하여 저장 (mermaid.ink 사용)
    try:
        import base64
        import requests
        import os
        from pathlib import Path
        
        # Mermaid 코드 인코딩
        # [Fix] 마크다운 코드 블록 제거 (```mermaid ... ```)
        raw_code = response.content.strip()
        if raw_code.startswith("```"):
            raw_code = raw_code.split("```")[1]
            if raw_code.startswith("mermaid"):
                raw_code = raw_code[7:]
        raw_code = raw_code.strip()
        
        graph_bytes = raw_code.encode("utf8")
```
