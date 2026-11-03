---
title: "src/agents/supervisor.py"
tags:
  - code
  - layer/agent
---

# `src/agents/supervisor.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__plan_core__logger]], [[mod__graph__edit_graph]], [[mod__models__llm]], [[mod__prompts__supervisor_prompt]], [[mod__state__base]]



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def supervisor_node(state)`
- `def summarize_messages(prompt, messages)`
- `def prepare_idea_structuring(state)`
- `def edit(state)`
- `def ask_user(state)`
- `def supervisor_router(state)`
- `def summary_state(state)`

## 소스 코드 미리보기 (`src/agents/supervisor.py`)

```python
from graph.edit_graph import edit_subgraph
from state.base import GlobalState
from models.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from prompts.supervisor_prompt import ROUTING_PROMPT, MESSAGE_SUMMARY_PROMPT, IDEA_SUMMARY_PROMPT, IDEA_SUMMARY_FORMAT, SUPERVISOR_CHAT_PROMPT
from langchain_core.output_parsers import JsonOutputParser

from agents.plan_core.logger import get_logger, LogLevel

def supervisor_node(state: GlobalState) -> GlobalState:
    logger = get_logger()
    last_action = state.get('supervision', {}).get('last_decision', 'None')
    plan_status = state.get('plan', {}).get('plan_status', 'None')
    
    logger.log(LogLevel.INFO, "supervisor", 
        f"Supervisor 진입 (Last Action: {last_action}, Plan Status: {plan_status})", {
            "last_decision": last_action,
            "plan_status": plan_status,
            "current_task": state.get('supervision', {}).get('current_task')
        })
    
    # 사용자 응답이 있는 경우
    if state['awaiting_input'] == True:
        # 기획서 수정 요청인 경우, Edit 호출
        if state['supervision']['edit_request']['require_edit'] == True:
            return {
                "messages": [
                    HumanMessage(content=state["user_response"])
                ],
                'awaiting_input': False,
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'RUN_EDIT',
                    'edit_request': {
                        **state['supervision']['edit_request'],
                        'require_edit': False,
                    },
                }
            }
        # 채팅 응답인 경우, 해당 내용을 메시지에 추가
        elif state['supervision']['request_type'] == 'text':
            return {
                "messages": [
                    HumanMessage(content=state["user_response"])
                ],
                'awaiting_input': False,
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'supervisor_node',
                }
            }
        # 질문지 응답인 경우, Idea Structuring 호출
        elif state['supervision']['request_type'] == 'idea_form':
            return {
                'awaiting_input': False,
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'RUN_IDEA_STRUCTURING',
                }
            }

    # 초기 상태
    if state['supervision']['last_decision'] == '':
        return {
            'supervision': {
                **state['supervision'],
                'last_decision': 'ASK_USER',
                'current_task': 'idea_structuring',
                'pending_request': '안녕하세요. 기획서 작성을 도와드릴까요?',
            }
        }
    
    # 기획서 작성 중 새로고침 후 리서치 필요 여부 확인
    elif state['supervision']['last_decision'] == 'Refresh':
        if state['plan']['plan_status'] == 'WAITING_FOR_RESEARCH':
            # 리서치가 필요한 경우 → Research Agent 호출
            logger.log(LogLevel.INFO, "supervisor", 
                f"Routing to RUN_RESEARCH (Section: {state['research']['section_context']})")
            return {
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'RUN_RESEARCH',
                    'current_task': 'research',
                    'pending_research_section': state['research']['section_context'],
                }
            }
        elif state['plan']['plan_status'] == 'IN_PROGRESS':
            # 아직 남은 섹션이 있는 경우 → Plan Agent 재호출 (Loop)
            logger.log(LogLevel.INFO, "supervisor", "Plan IN_PROGRESS. Looping RUN_PLANNING...")
            return {
```
