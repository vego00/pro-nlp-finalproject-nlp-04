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
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'RUN_PLANNING',
                    'current_task': 'planning',
                }
            }
    # 서브에이전트 호출 이후
    elif state['supervision']['last_decision'] not in ['ASK_USER', 'supervisor_node']:
        last_decision = state['supervision']['last_decision']

        # 아이디어 에이전트 호출 이후
        if last_decision == 'RUN_IDEA_STRUCTURING':
            # 유저의 추가 입력이 필요한 경우 (질문지 처리 필요)
            if state['idea']['last_decision'] == 'WAIT_FOR_USER':
                return {
                    'supervision': {
                        **state['supervision'],
                        'last_decision': 'ASK_USER',
                        'current_task': 'idea_structuring',
                        'pending_request': state['idea']['form'],
                        'request_type': 'idea_form',
                    }
            }
            # 아이디어 에이전트 컨펌 or 완료
            elif state['idea']['last_decision'] in ['CONFIRM', 'COMPLETE']:
                return {
                    'completed_steps': 'idea_structuring',
                    'supervision': {
                        **state['supervision'],
                        'last_decision': 'RUN_PLANNING',
                        'current_task': 'planning',
                    }
                }
        elif last_decision == 'RUN_PLANNING':
            # 기획서 작성 중 (섹션별 생성시마다 페이지 새로고침)
            if state['plan']['plan_status'] in ['WAITING_FOR_RESEARCH', 'IN_PROGRESS']:
                return {
                    'supervision': {
                        **state['supervision'],
                        'last_decision': 'Refresh',
                        'request_type': 'text',
                    }
                }
            
            # 기획서 작성 완료 (모든 섹션 생성 완료)
            logger.log(LogLevel.INFO, "supervisor", "Plan COMPLETED. Asking User.")
            return {
                'completed_steps': 'planning',
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'ASK_USER',
                    'current_task': 'planning',
                    'pending_request': '기획서 작성이 완료되었습니다. 추가 수정이 필요하신 부분을 알려주세요.',
                }
            }
        
        elif last_decision == 'RUN_RESEARCH':
            # =====================================================
            # [Research 연동] Research Agent 실행 완료 후 처리
            # 
            # Research Agent 실행 결과:
            #   - state['research']['gathered_evidence']: 수집된 검색 결과
            #   - state['research']['analysis_result']: 분석 결과 텍스트
            #   - state['research']['needs_research']: False로 설정됨
            # 
            # 다시 Plan Agent로 돌아가서 동일 섹션 생성 재개
            # (current_section_index는 그대로 유지되어 있음)
            # =====================================================
            return {
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'RUN_PLANNING',
                    'current_task': 'planning',
                }
            }
        elif last_decision == 'RUN_EDIT':
            return {
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'ASK_USER',
                    'current_task': 'planning',
                    'pending_request': '기획서 수정이 완료되었습니다. 추가 수정이 필요하신 부분을 알려주세요.',
                }
            }
    # 사용자 응답과 현재 상태를 파악 후, 분기
    else:
        routing_context = summary_state(state)
        response = get_llm(max_tokens=10000, json_mode=True).invoke([
            SystemMessage(content=ROUTING_PROMPT),
            HumanMessage(content=routing_context),
            ])
        response_json = JsonOutputParser().parse(response.content)
        logger.log(LogLevel.DEBUG, "supervisor", f"Router LLM Decision: {response_json.get('next_action')}", {
            "decision": response_json
        })
        return {
            'supervision': {
                **state['supervision'],
                'last_decision': response_json['next_action'],
                'current_task': response_json['next_action'],
                'reason': response_json['reason'],
                'summary': routing_context,
            }
        }

def summarize_messages(prompt: str, messages: list[BaseMessage]) -> str:
    if not messages:
        return ""

    joined_msgs = IDEA_SUMMARY_FORMAT.format(user_messages="- " + "\n- ".join([f"{m.type}: {m.content}" for m in messages]))

    result = get_llm(max_tokens=10000).invoke([SystemMessage(content=prompt), HumanMessage(content=joined_msgs)])
    return result.content.strip()

def prepare_idea_structuring(state: GlobalState) -> GlobalState:
    # [Fix] 웹 폼 입력(Dict)인 경우 요약 과정을 건너뛰고 그대로 전달
    if isinstance(state.get('user_response'), dict):
        return {}

    if state['supervision']['request_type'] == 'text':
        user_msgs = [m for m in state['messages'] if isinstance(m, HumanMessage) and m.content]
        user_idea = summarize_messages(IDEA_SUMMARY_PROMPT, user_msgs)
        return {
            'user_response': user_idea,
            'supervision': {
                **state['supervision'],
                'request_type': 'text',
            }
        }
    return {}

def edit(state: GlobalState) -> GlobalState:
    edit_state = {
        **state,
        'target_section_id': state['supervision']['edit_request']['target_section_id'],
        'instruction': state['supervision']['edit_request']['instruction'],
        'granularity': state['supervision']['edit_request']['granularity'],
        'edit_range_start': state['supervision']['edit_request']['edit_range_start'],
    }

    result = edit_subgraph.invoke(edit_state)
    return {"plan": result.get("plan", state["plan"])}

def ask_user(state: GlobalState) -> GlobalState:
    # 다른 에이전트가 사용자에게 전달할 내용이 있을 시
    if state['supervision']['pending_request']:
        if state['supervision']['request_type'] == 'text':
            return {
                'supervision': {
                    **state['supervision'],
                    'pending_request': None,
                },
                "messages": [
                    AIMessage(content=state['supervision']['pending_request'])
                ],
                'input_request': state['supervision']['pending_request'],
                "awaiting_input": True,
            }
        elif state['supervision']['request_type'] == 'idea_form':
            return {
                'supervision': {
                    **state['supervision'],
                    'pending_request': None,
                },
                'input_request': state['supervision']['pending_request'],
                "awaiting_input": True,
            }
    # 수퍼바이저와 사용자와의 대화시
    else:
        # 현재 상태와 메시지 기록을 바탕으로 생성된 응답을 사용자에게 전달
        response = get_llm(max_tokens=10000).invoke([SystemMessage(content=SUPERVISOR_CHAT_PROMPT), HumanMessage(content=state['supervision']['summary'])])
        return {
            "messages": [
                AIMessage(content=response.content)
            ],
            'input_request': response.content,
            "awaiting_input": True,
        }

def supervisor_router(state: GlobalState) -> str:
    return state['supervision']['last_decision']


# 필요한 내용
# 1. goal
# 2. completed_steps
# 3. current_outputs
# 4. missing_information
# 5. known_constraints
# 6. last_user_input
# 7. message_history
# 8. confidence_levels (if provided)
def summary_state(state: GlobalState) -> str:
    completed_steps = state['completed_steps']

    current_outputs = {}
    if "idea" in state:
        current_outputs["idea_structuring"] = [
            f"{section['title']}: {section['guideline']}"
            for section in state["idea"].get("blueprint", [])
            if section.get("is_required_from_user") == False
        ]
    
    if "plan" in state:
        current_outputs["planning"] = state["plan"].get("final_markdown", "")
    
    required_info = [section.get('title') for section in state['idea']['blueprint']]
    
    filled_info = [section.get('title') for section in state['idea']['blueprint'] if section.get('is_required_from_user') == False]
    missing_information = [title for title in required_info if title not in filled_info]

    message_history = summarize_messages(MESSAGE_SUMMARY_PROMPT, state["messages"])
    
    return f'''
        Goal: {state['supervision']['goal']}
        Completed steps: {completed_steps}
        Current task: {state['supervision']['current_task']}
        Current outputs: {current_outputs}
        Required information: {required_info}
        Missing information: {missing_information}
        Message history: {message_history}
        Last user input: {state['user_response']}
        '''
        # Confidence levels: {state['supervision']['confidence_levels']}
