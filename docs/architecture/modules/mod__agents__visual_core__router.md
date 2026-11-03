---
title: "src/agents/visual_core/router.py"
tags:
  - code
  - layer/agent
---

# `src/agents/visual_core/router.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__plan_core__logger]], [[mod__agents__visual_core__schemas]], [[mod__models__llm]]

> 시각화 결정 라우터 - 섹션 내용을 분석하여 필요한 시각화 유형 결정

## 정의된 클래스 / 상태 스키마
- `RouterState`

## 정의된 함수 / 노드
- `def decide_node(state)`
- `def generate_visual_meta(state)`
- `def route_next(state)`

## 소스 코드 미리보기 (`src/agents/visual_core/router.py`)

```python
"""
시각화 결정 라우터 - 섹션 내용을 분석하여 필요한 시각화 유형 결정
"""
from __future__ import annotations
from typing import Any, Dict, TypedDict

from models.llm import get_llm
from agents.visual_core.schemas import Decision, VisualMeta
from agents.plan_core.logger import get_logger, LogLevel


class RouterState(TypedDict, total=False):
    section_id: str
    section_title: str
    section_text: str
    rule_hints: Dict[str, Any]
    decision: Dict[str, Any]
    visual_meta: Dict[str, Any]
    artifacts: Dict[str, Any]


def decide_node(state: RouterState) -> RouterState:
    """
    Solar Pro 2 LLM을 사용하여 시각화 필요성 판단
    """
    text = state.get("section_text") or ""
    title = state.get("section_title") or ""
    
    
    # LLM 호출, 라우팅은 빠른 판단을 위해 low 사용
    chat = get_llm(max_tokens=8192, reasoning_effort="low")
    structured_llm = chat.with_structured_output(Decision)
    
    prompt_text = f"""
    당신은 기획서 작성 도우미의 두뇌 역할을 하는 Router입니다.
    사용자가 작성한 기획서의 '섹션 제목'과 '내용'을 보고, 
    이 내용을 시각화하기 위해 표(Table), 다이어그램(Diagram), 차트(Chart), 이미지 검색(Search), 이미지 생성(Gen) 
    중 어떤 도구가 필요한지 판단하세요.

    [입력 정보]
    - 섹션 제목: {title}
    - 섹션 텍스트: {text}

    [판단 기준]
    1. Table: 정형 데이터, 비교, 요금표, 로드맵, 지표 등이 포함되면 True.
    2. Diagram: 구조, 흐름, 순서, 관계 등이 텍스트로 설명되어 있어 시각화가 좋으면 True (Mermaid 사용).
    3. Chart: 수치 데이터의 비중, 시간 흐름, 항목 간 수치 비교 등이 명확하여 시각적 그래프가 필요하면 True (Plotly 사용).
       - 반드시 chart_type(pie, bar, line, scatter) 중 하나를 선택하세요.
    4. Image Search: UI 참고, 레퍼런스, 실제 사례 이미지를 보고 싶어하면 True.
    5. Image Gen: "그려줘", "생성해줘", "일러스트" 등 없는 이미지를 만들어야 하면 True.

    필요한 도구와 그 구체적인 타입(table_type, diagram_type, chart_type)을 결정하고, 
    검색이나 생성이 필요하다면 쿼리/프롬프트도 제안하세요.
    차트와 표가 동시에 필요해 보인다면, 더 직관적인 'Chart'를 우선적으로 선택하세요.
    """
    
    try:
        decision = structured_llm.invoke(prompt_text)
    except Exception as e:
        print(f"LLM Error: {e}")
        decision = Decision(reason=f"Error: {str(e)}")

    if decision is None:
        decision = Decision(reason="LLM returned None")

    state["decision"] = decision.model_dump()
    return state


def generate_visual_meta(state: RouterState) -> RouterState:
    """
    시각화가 필요한 경우, 왜 필요한지 메타데이터 생성
    """
    decision = Decision(**state.get("decision", {}))
    text = state.get("section_text", "")
    title = state.get("section_title", "")
    
    if not any([decision.needs_table, decision.needs_diagram, decision.needs_chart,
                decision.needs_image_search, decision.needs_image_gen]):
        state["visual_meta"] = None
        return state
    
    # 시각화 타입 결정
    if decision.needs_table:
        visual_type = "table"
    elif decision.needs_diagram:
        visual_type = "diagram"
    elif decision.needs_image_search:
        visual_type = "image_search"
    else:
```
