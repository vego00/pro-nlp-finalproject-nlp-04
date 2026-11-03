---
title: "src/agents/idea.py"
tags:
  - code
  - layer/agent
---

# `src/agents/idea.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__plan_core__logger]], [[mod__models__llm]], [[mod__prompts__idea_prompts]], [[mod__state__idea]]



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def idea_router(state)`
- `def analyzer_node(state)`
- `def creator_node(state)`
- `def updater_node(state)`
- `def questioner_node(state)`
- `def evaluator_node(state)`
- `def idea_eval_router(state)`

## 소스 코드 미리보기 (`src/agents/idea.py`)

```python
import sys
import os

# 현재 파일의 부모의 부모 폴더(src)를 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from state.idea import InternalState
from models.llm import get_mini_llm, get_llm
from prompts.idea_prompts import CREATOR_PROMPT, UPDATER_PROMPT, QUESTIONER_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.plan_core.logger import get_logger, LogLevel

def idea_router(state: InternalState) -> str:
    # analyzer에서 정한 intent를 가져옴
    intent = state.get('internal_user_intent')
    
    # 새로 짜야 하는 경우
    if intent == "RESTRUCTURE":
        return "creator"
    # 부분 수정만 필요한 경우
    elif intent == "FILL_CONTENT":
        return "updater"
    
    # 기본값은 일단 다시 질문함
    return "questioner"

def analyzer_node(state: InternalState):
    logger = get_logger()
    user_input = state.get('user_response')
    blueprint = state.get('blueprint') or state.get('idea', {}).get('blueprint')
    
    if isinstance(user_input, dict) and blueprint:
        return {
            "internal_user_intent": "FILL_CONTENT",
            "target_sections": list(user_input.keys()),
        }
    elif not blueprint:
        return {
            "internal_user_intent": "RESTRUCTURE", 
            "target_sections": None,
        }
    else: #혹시 모를 예외 케이스: blueprint는 있는데 자연어가 들어온 경우
        return {
            "internal_user_intent": "RESTRUCTURE", 
            "target_sections": None,
        }


def creator_node(state: InternalState):
    logger = get_logger()
    system_msg = SystemMessage(content=CREATOR_PROMPT)
    user_input = state['user_response']
    llm = get_llm(temperature=0.3, max_tokens=5000, reasoning_effort='high', json_mode=True)
    
    # 현재 상황(Context)을 LLM이 알기 쉽게 정리
    context_info = f"""
    blueprint: {state['idea'].get('blueprint') or []}
    """

    response = llm.invoke([
        system_msg,
        HumanMessage(content=f"{context_info}\n\n유저 요청: {user_input}")
    ])

    result = json.loads(response.content)
    
    # 블루프린트 생성 결과 로깅
    logger.log(LogLevel.INFO, "idea_creator", f"Creator 노드 완료 (style: {result['planning_style']})", {
        "planning_style": result['planning_style'],
        "rationale": result['rationale'][:200] if result.get('rationale') else None,
        "blueprint_count": len(result.get('blueprint', [])),
        "blueprint_titles": [b.get('title') for b in result.get('blueprint', [])]
    })
    
    return {
        "idea":
            {   
                **state['idea'],
                "planning_style": result['planning_style'], 
                "rationale": result['rationale'],
                "blueprint": result['blueprint'],   
            },
        "target_sections": None,
    }
    
def updater_node(state: InternalState):
    logger = get_logger()
    system_msg = SystemMessage(content=UPDATER_PROMPT)
    user_input = state['user_response']
```
