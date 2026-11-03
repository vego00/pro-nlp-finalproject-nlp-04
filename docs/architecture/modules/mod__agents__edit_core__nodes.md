---
title: "src/agents/edit_core/nodes.py"
tags:
  - code
  - layer/agent
---

# `src/agents/edit_core/nodes.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__plan]], [[mod__agents__plan_core__generator]], [[mod__agents__plan_core__schemas]], [[mod__prompts__edit_prompts]], [[mod__state__edit]]

> Edit Pipeline Nodes

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def regenerate_node(state)`
- `def _calculate_section_index(state)`
- `def _calculate_range_end(lines, start_idx, granularity)`

## 소스 코드 미리보기 (`src/agents/edit_core/nodes.py`)

```python
"""
Edit Pipeline Nodes
"""
from agents.plan_core.generator import generate_section_from_blueprint, generate_partial_edit
from agents.plan_core.schemas import StructuredInput, BlueprintItem
from state.edit import EditInternalState
from prompts.edit_prompts import SECTION_REGENERATION_GUIDELINE_TEMPLATE

from agents.plan import apply_edit_to_plan

def regenerate_node(state: EditInternalState) -> EditInternalState:
    """
    섹션 또는 부분(문단/문장) 재생성 노드
    """

    # GlobalState에서 데이터 추출
    blueprint_list = state.get("idea", {}).get("blueprint", [])
    if not blueprint_list:
        print(f"[Edit] Error: Blueprint not found.")
        return state

    # [Fix] target의 section index 찾기
    blueprint_index = _calculate_section_index(state)
    if blueprint_index >= len(blueprint_list):
        print(f"[Edit] Error: Blueprint index out of range.")
        return state

    # 1. Target Blueprint Item 가져오기
    target_item_dict = blueprint_list[blueprint_index]
    target_item = BlueprintItem(**target_item_dict)
    
    granularity = state.get("granularity", "section")
    range_start = state.get("edit_range_start")
    
    # -------------------------------------------------------
    # Case A: Section Edit (전체 재생성)
    # -------------------------------------------------------
    if granularity == "section":
        print(f"[Edit] 섹션 전체 재생성 모드")
        
        # Instruction Injection
        original_guideline = target_item.guideline or ""
        
        # Feedback Injection (If Retry)
        feedback_section = ""
        if state.get("feedback"):
            feedback_section = f"\n\n[PREVIOUS FEEDBACK (Must Fix)]: {state['feedback']}"
            print(f"[Edit] 피드백 반영하여 재생성: {state['feedback']}")
            
        injected_guideline = SECTION_REGENERATION_GUIDELINE_TEMPLATE.format(
            original_guideline=original_guideline,
            instruction=state['instruction'],
            feedback_section=feedback_section
        )
        
        # 수정된 아이템 생성 (Generator에 전달용)
        modified_item = BlueprintItem(
            title=target_item.title,
            guideline=injected_guideline,
            content=""
        )
        
        # StructuredInput 구성
        idea = state.get("idea", {})
        structured_input = StructuredInput(
            planning_style=idea.get("planning_style", "General"),
            rationale=idea.get("rationale", ""),
            toc=idea.get("toc", []),
            blueprint=[BlueprintItem(**b) for b in blueprint_list]
        )
        
        # Generator 호출
        new_section = generate_section_from_blueprint(
            structured_input=structured_input,
            blueprint_item=modified_item,
            section_index=blueprint_index,
            previous_sections=[] 
        )
        
        # 결과 저장
        state["regenerated_content"] = new_section.content
        state["used_guideline"] = injected_guideline
        state["section_index"] = blueprint_index
        print(f"[Edit] 재생성 완료 (Length: {len(new_section.content)})")
        
        # [Persistence] 수정 사항 즉시 반영 및 저장
        updated_state = apply_edit_to_plan(state, blueprint_index, new_section.content)
        state["plan"] = updated_state.get("plan") # Update plan in local state
        
        return state
```
