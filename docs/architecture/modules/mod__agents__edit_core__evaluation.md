---
title: "src/agents/edit_core/evaluation.py"
tags:
  - code
  - layer/agent
---

# `src/agents/edit_core/evaluation.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__models__llm]], [[mod__state__edit]]

> Edit Pipeline Evaluation Node

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def evaluate_node(state)`
- `def route_evaluation(state)`

## 소스 코드 미리보기 (`src/agents/edit_core/evaluation.py`)

```python
"""
Edit Pipeline Evaluation Node
"""
from typing import Dict, Any, Literal
from langchain_core.messages import SystemMessage, HumanMessage
from models.llm import get_llm
from state.edit import EditInternalState

def evaluate_node(state: EditInternalState) -> EditInternalState:
    """
    재생성된 섹션이 유저의 수정 요청을 잘 반영했는지 평가합니다.
    """
    print(f"[Eval] 섹션 평가 중...")
    
    current_content = state.get("regenerated_content", "")
    instruction = state.get("instruction", "")
    original_guideline = ""
    
    # Context에서 원래 가이드라인 추출 (있는 경우)
    blueprint = state.get("idea", {}).get("blueprint", [])
    if blueprint and "match_section_index" in state:
        idx = state["match_section_index"]
        # Index range check
        if 0 <= idx < len(blueprint):
            original_guideline = blueprint[idx].get("guideline", "")

    # LLM Evaluator
    chat = get_llm(max_tokens=1000, reasoning_effort="medium")
    
    system_prompt = """당신은 까다로운 콘텐츠 에디터입니다.
    사용자의 '수정 요청(Instruction)'이 '결과물(Regenerated Content)'에 제대로 반영되었는지 검증하세요.
    
    검증 기준:
    1. Instruction의 핵심 요구사항이 포함되어 있는가?
    2. 기존 문맥과 너무 동떨어지거나, 앞뒤가 안 맞는 내용이 되지는 않았는가?
    
    출력 형식:
    [PASS] 또는 [FAIL]로 시작하고, 그 뒤에 이유를 한 줄로 작성하세요.
    예: [PASS] 에너지 효율 관련 단점이 잘 추가됨.
    예: [FAIL] 전력 소모에 대한 언급이 전혀 없음.
    """
    
    user_message = f"""
    [Original Guideline]: {original_guideline}
    [User Instruction]: {instruction}
    
    [Regenerated Content]:
    {current_content}
    """
    
    response = chat.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ])
    
    result_text = response.content.strip()
    print(f"[Eval] 결과: {result_text}")
    
    state["critique"] = result_text
    
    if result_text.startswith("[PASS]"):
        state["feedback"] = None # 통과
    else:
        # 실패 시 피드백 생성 (다음 regeneration에 반영)
        reason = result_text.replace("[FAIL]", "").strip()
        state["feedback"] = f"이전 생성 실패 사유: {reason}. 이 점을 보완해서 다시 작성하세요."
        # retry_count 증가
        state["retry_count"] = state.get("retry_count", 0) + 1
        
    return state


def route_evaluation(state: EditInternalState) -> Literal["regenerate", "end"]:
    """
    평가 결과에 따른 라우팅
    """
    retry_count = state.get("retry_count", 0)
    
    # 1. Feedback이 없으면 통과
    if not state.get("feedback"):
        return "end"
        
    # 2. 최대 재시도 횟수 초과 시 강제 통과 (무한루프 방지)
    if retry_count >= 3:
        print(f"[Eval] 재시도 횟수 초과({retry_count}). 강제 종료합니다.")
        return "end"
        
    # 3. 실패 및 재시도 가능 -> 재생성으로 이동
    print(f"[Eval] 재시도 요청 ({retry_count}/3)")
    return "regenerate"
```
