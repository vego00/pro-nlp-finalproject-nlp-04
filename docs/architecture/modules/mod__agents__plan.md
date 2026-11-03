---
title: "src/agents/plan.py"
tags:
  - code
  - layer/agent
---

# `src/agents/plan.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__plan_core__generator]], [[mod__agents__plan_core__logger]], [[mod__agents__plan_core__pipeline]], [[mod__agents__plan_core__schemas]], [[mod__agents__visual_core__schemas]], [[mod__state__base]], [[mod__state__plan]]

> Plan Agent Adapter Functions (Facade)

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def apply_edit_to_plan(state, section_index, new_content)`
- `def plan_generate(state)`
- `def plan_evaluate(state)`
- `def plan_eval_router(state)`

## 소스 코드 미리보기 (`src/agents/plan.py`)

```python
"""
Plan Agent Adapter Functions (Facade)
InternalState(GlobalState) 패턴 적용
"""
from typing import Dict, Any
from state.base import GlobalState
from state.plan import PlanInternalState
from agents.plan_core.pipeline import plan_pipeline
from agents.plan_core.logger import get_logger, LogLevel
from agents.plan_core.schemas import GeneratedPlan, PlanSection, StructuredIdea, TableOfContents, TableOfContentsItem
from agents.plan_core.generator import compose_plan_markdown
from agents.visual_core.schemas import VisualArtifact

def apply_edit_to_plan(state: GlobalState, section_index: int, new_content: str) -> GlobalState:
    """
    수정된 섹션 내용을 반영하고, 마크다운을 재생성하여 파일에 저장합니다.
    """
    logger = get_logger()
    
    # 1. Update Sections
    plan_data = state.get("plan", {})
    sections = plan_data.get("sections", [])
    
    if 0 <= section_index < len(sections):
        sections[section_index]['content'] = new_content
        logger.log(LogLevel.INFO, "plan_edit", f"Section {section_index} Updated.", {})
        
        # 2. Re-compose Markdown
        idea_data = state.get("idea", {})
        
        # Reconstruct objects for generator
        toc_items = []
        for i, title in enumerate(idea_data.get("toc", [])):
            parts = title.split(". ", 1)
            toc_items.append(TableOfContentsItem(
                section_number=parts[0] if len(parts) > 1 else str(i + 1),
                title=parts[1] if len(parts) > 1 else title
            ))

        plan_obj = GeneratedPlan(
            idea=StructuredIdea(
                title=idea_data["toc"][0].split(". ", 1)[-1] if idea_data.get("toc") else "기획서",
                summary=idea_data.get("rationale", ""),
                problem="", target_users=[], core_features=[], differentiators=[]
            ),
            toc=TableOfContents(items=toc_items),
            sections=[PlanSection(**s) for s in sections],
            method="blueprint"
        )
        
        visual_artifacts_data = plan_data.get('visual_artifacts', [])
        visual_artifacts = [VisualArtifact(**v) for v in visual_artifacts_data]
        
        new_markdown = compose_plan_markdown(plan_obj, visual_artifacts)
        
        # 3. Save to File (Overwrite)
        output_path = plan_data.get('output_path')
        if output_path:
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(new_markdown)
                logger.log(LogLevel.INFO, "plan_edit", f"File saved to {output_path}", {})
            except Exception as e:
                logger.log(LogLevel.ERROR, "plan_edit", f"Failed to save file: {e}", {})
        
        # 4. Return updated state
        updated_plan = plan_data.copy()
        updated_plan.update({
            "sections": sections,
            "final_markdown": new_markdown
        })
        state["plan"] = updated_plan
        return state
        
    else:
        logger.log(LogLevel.ERROR, "plan_edit", f"Section index {section_index} out of range.", {})
        return state

def plan_generate(state: GlobalState) -> GlobalState:
    """
    [진입점] GlobalState를 기반으로 PlanInternalState를 초기화하여 내부 파이프라인 실행
    """
    # 1. 초기 내부 상태 구성
    # GlobalState의 모든 내용을 복사하고, Plan 전용 변수들을 초기화합니다.
    plan_data = state.get("plan", {})
    
    # =====================================================
    # [Research 연동] current_section_index 유지
    # 
    # 리서치 후 재호출 시 동일 섹션부터 재개하기 위해
```
