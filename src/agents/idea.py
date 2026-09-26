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
    llm = get_llm(temperature=0.5, max_tokens=5000, reasoning_effort='high', json_mode=True)
    
    # 현재 상황(Context)을 LLM이 알기 쉽게 정리
    context_info = f"""
    blueprint: {state['idea'].get('blueprint')}
    required_data_points : {state.get('required_data_points', '')}
    target_sections: {state.get('target_sections')}
    """

    response = llm.invoke([
        system_msg,
        HumanMessage(content=f"{context_info}\n\n유저 요청: {user_input}")
    ])

    result = json.loads(response.content)
    
    # 블루프린트 업데이트 결과 로깅
    logger.log(LogLevel.INFO, "idea_updater", "Updater 노드 완료", {
        "target_sections": state.get('target_sections'),
        "blueprint_count": len(result.get('blueprint', [])),
        "blueprint_titles": [b.get('title') for b in result.get('blueprint', [])]
    })
    
    return {
        "idea":{
            **state['idea'],
            "blueprint": result['blueprint']
        },
        "target_sections": None,
        "required_data_points": None,
    }

def questioner_node(state: InternalState):
    system_msg = SystemMessage(content=QUESTIONER_PROMPT)
    llm = get_mini_llm(temperature=0.5, max_tokens=4000, json_mode=True)

    intent = state.get("internal_user_intent")
    # 의도가 불분명한 경우 (AMBIGUOUS)
    if intent == "AMBIGUOUS":
        # AI가 유저에게 다시 물어보는 프롬프트 생성
        response = llm.invoke(f"유저의 입력 '{state['user_input']}'이 모호합니다. 어떤 섹션을 수정하고 싶은지, 혹은 무엇을 도와드리면 될지 친절하게 되물어주세요.")
        return {
            "idea": {
                **state["idea"], 
                "last_decision": "WAIT_FOR_USER", 
                "messages": response.content
            }
        }
    
    
    blueprint = state['idea'].get('blueprint')
    not_completed_count = len([s for s in blueprint if s['is_required_from_user']])

    if not_completed_count == 0:
        # 더 이상 물어볼 게 없다면는 경우
        return {
            "idea": {
                **state["idea"],
                "messages": "모든 기획 섹션이 완료되었습니다! 최종 검토를 시작합니다.",
            },
            "internal_user_intent": "CONFIRM"
        }
    
    # 현재 상황(Context)을 LLM이 알기 쉽게 정리
    context_info = f"""
    blueprint: {blueprint}
    """

    response = llm.invoke([
        system_msg,
        HumanMessage(content=f"{context_info}")
    ])
    result = json.loads(response.content)
    
    # =====================================================
    # [검증] LLM 응답의 options 구조 검증 및 보정
    # 
    # LLM이 가끔 value 키를 누락하거나 다른 형태로 반환할 수 있음
    # ui_components.py에서 KeyError 방지를 위해 여기서 검증
    # =====================================================
    forms = result.get("forms", [])
    for form in forms:
        options = form.get("options", [])
        validated_options = []
        for opt in options:
            if isinstance(opt, dict):
                validated_options.append({
                    "label": opt.get("label", str(opt)),
                    "value": opt.get("value", opt.get("description", ""))
                })
            elif isinstance(opt, str):
                validated_options.append({
                    "label": opt,
                    "value": ""
                })
        form["options"] = validated_options
        
        # [Log] guide_text가 없으면 빈 문자열로 보정하여 UI 에러 방지
        if "guide_text" not in form:
            form["guide_text"] = ""
    
    return {
        "idea":{
            **state['idea'],
            "form": forms
        },
        "required_data_points": forms
    }

def evaluator_node(state: InternalState):
    logger = get_logger()
    # 검수 로직  
    blueprint = state['idea'].get('blueprint', [])
    is_valid = True # 검증 로직 결과
    
    if not is_valid:
        logger.log(LogLevel.WARNING, "idea_evaluator", "Evaluator 노드: 검증 실패 (REJECTED)", {})
        return {
            "idea": {
                **state['idea'],
                "last_decision": "REJECTED", 
            }
        }

    # 검수 통과 시: 다음 단계 준비
    remaining_sections = [s for s in blueprint if s.get('is_required_from_user') == True]
    
    if not remaining_sections:
        # 모든 데이터가 수집됨
        decision = "COMPLETE"
        state["idea"]["toc"] = [section.get('title') for section in blueprint]
    else:
        # 유저의 추가 입력이 필요함
        decision = "WAIT_FOR_USER"
    
    # 최종 결과 로깅 (COMPLETE인 경우 블루프린트 전체 내용 로깅)
    log_data = {
        "decision": decision,
        "remaining_sections_count": len(remaining_sections),
        "total_sections": len(blueprint)
    }
    if decision == "COMPLETE":
        log_data["final_blueprint"] = blueprint
        log_data["toc"] = [section.get('title') for section in blueprint]
    
    logger.log(LogLevel.INFO, "idea_evaluator", f"Evaluator 노드 완료 (decision: {decision})", log_data)
    
    return {
        "idea":{
            **state['idea'],
            "last_decision": decision
        }
    }

def idea_eval_router(state: InternalState) -> str:
    # 평가 결과에 따라 pass retry 결정
    return "pass"
