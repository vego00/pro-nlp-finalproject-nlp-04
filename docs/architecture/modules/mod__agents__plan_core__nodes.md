---
title: "src/agents/plan_core/nodes.py"
tags:
  - code
  - layer/agent
---

# `src/agents/plan_core/nodes.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__plan_core__evaluator]], [[mod__agents__plan_core__generator]], [[mod__agents__plan_core__logger]], [[mod__agents__plan_core__schemas]], [[mod__agents__visual_core__schemas]], [[mod__models__llm]], [[mod__prompts__plan_prompts]], [[mod__state__plan]]

> 오케스트레이터 노드 함수들 - 기획서 생성 워크플로우의 개별 노드들

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def parse_input_node(state)`
- `def initialize_output_node(state)`
- `def generate_section_node(state)`
- `def process_visual_node(state)`
- `def append_section_node(state)`
- `def increment_section_index_node(state)`
- `def route_next_section(state)`
- `def compose_output_node(state)`
- `def refine_plan_node(state)`
- `def save_output_node(state)`

## 소스 코드 미리보기 (`src/agents/plan_core/nodes.py`)

```python
"""
오케스트레이터 노드 함수들 - 기획서 생성 워크플로우의 개별 노드들
"""
from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from models.llm import get_llm


from agents.plan_core.schemas import (
    StructuredIdea, TableOfContents, TableOfContentsItem, 
    PlanSection, GeneratedPlan,
    BlueprintItem, StructuredInput
)
from agents.plan_core.generator import (
    compose_plan_markdown, generate_section_from_blueprint,
    format_plan_header, format_plan_toc, format_section_content
)

from state.plan import PlanInternalState
from agents.plan_core.logger import get_logger, LogLevel
from agents.plan_core.evaluator import evaluate_research_need
from agents.visual_core import run_visual_for_section, VisualArtifact


# ===========================
# 기획서 생성 노드들 (Blueprint 기반)
# ===========================

def parse_input_node(state: PlanInternalState) -> PlanInternalState:
    """전역 상태에서 필요한 입력값을 내부 상태로 전이 및 초기화"""
    print("[Pipeline] 입력 데이터 확인 및 초기화...")
    
    # IdeaState 및 PlanState(Public) 참조
    idea = state.get("idea", {})
    blueprint = idea.get("blueprint", [])
    
    # tqdm 제거
    total_sections = len(blueprint)

    
    # toc 변환 (문자열 목록 -> TableOfContents)
    toc_items = []
    for i, title in enumerate(idea.get("toc", [])):
        parts = title.split(". ", 1)
        section_number = parts[0] if len(parts) > 1 else str(i + 1)
        section_title = parts[1] if len(parts) > 1 else title
        toc_items.append({
            "section_number": section_number,
            "title": section_title,
            "guideline": None
        })
    
    # PlanInternalState 필드 업데이트
    # (GlobalState를 상속받으므로 직접 할당)
    # [Fix] 기존 상태가 있으면 초기화하지 않음 (Resume 지원)
    if "current_section_index" not in state:
        state["current_section_index"] = 0
    if "sections" not in state:
        state["sections"] = []
    if "visual_artifacts" not in state:
        state["visual_artifacts"] = []
    
    # plan_status 초기화 (없으면 기본값)
    if "plan_status" not in state:
        state["plan_status"] = "IN_PROGRESS"
    
    state["temp_visual_state"] = {}
    state["final_markdown"] = ""
    # [Fix] output_path 초기화 제거 (agents/plan.py에서 전달된 값 유지)
    if "output_path" not in state:
        state["output_path"] = ""
    
    return state


def initialize_output_node(state: PlanInternalState) -> PlanInternalState:
    """출력 파일 생성 및 헤더/목차 초기화 (Incremental Saving)"""
    
    # [Fix] 이미 파일이 생성되어 있다면 스킵 (반복 실행 시 파일 유지)
    if state.get("output_path") and Path(state["output_path"]).exists():
        print(f"[Pipeline] 기존 출력 파일 유지: {state['output_path']}")
        return state

    print("[Pipeline] 출력 파일 초기화 중...")
    
    project_root = Path(__file__).parent.parent.parent.parent
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)
```
