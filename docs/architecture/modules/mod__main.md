---
title: "src/main.py"
tags:
  - code
  - layer/code
---

# `src/main.py`

- **소속 계층 태그**: `#layer/code`
- **상위 아키텍처 노트**: [[00-Index]]
- **내부 모듈 의존성(Imports)**: [[mod__front__ui_components]], [[mod__graph__supervisor_graph]]



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def create_initial_state()`

## 소스 코드 미리보기 (`src/main.py`)

```python
import streamlit as st
from graph.supervisor_graph import supervisor_app
from langchain_core.messages import HumanMessage, AIMessage
from front.ui_components import init_page, render_question_view, render_plan_view

# root에서 uv run streamlit run src/main.py 로 실행

init_page()

# 초기 상태 생성 함수
def create_initial_state():
    return {
        "messages": [],
        "awaiting_input": False,
        "input_request": None,
        "user_response": None,
        "completed_steps": [],
        "idea": {
            "planning_style": "",
            "rationale": "",
            "toc": [],
            "blueprint": [],
            "last_decision": "",
            "messages": "",
        },
        "plan": {
            "sections": [],
            "final_markdown": "",
            "output_path": "",
            "visual_artifacts": {},
        },
        "supervision": {
            "goal": "Produce a high-quality vibe-based planning document",
            "last_decision": "",
            "current_task": None,
            "reason": "",
            "pending_request": None,
            "request_type": "text",
            "edit_request": {
                'target_section_id': None,
                'require_edit': False,
                "instruction": "",
                "granularity": "",
                "edit_range_start": 0,
            }
        },
    }

# 세션 상태 초기화
if "state" not in st.session_state:
    st.session_state.state = supervisor_app.invoke(create_initial_state())
    st.session_state.phase = 'Waiting User Input'

if st.session_state.state['supervision']['last_decision'] == 'Refresh':
    st.session_state.phase = 'planning'

# 좌측 Sidebar (자료 영역)
with st.sidebar:
    st.title("Vibe Planner")
    st.markdown("---")

    st.subheader("📁 Research Materials")
    
    # [Fix] 섹션별 리서치 자료 동적 표시
    plan_data = st.session_state.state.get("plan", {})
    sections = plan_data.get("sections", [])
    
    has_evidence = False
    for sec in sections:
        evidence = sec.get("evidence", [])
        if evidence:
            has_evidence = True
            with st.expander(f"{sec.get('section_number', '')}. {sec.get('title', 'Untitled')}", expanded=False):
                for item in evidence:
                    st.markdown(f"- {item}", unsafe_allow_html=True)

    if not has_evidence:
        st.info("생성된 리서치 자료가 없습니다.")

# 메인 3단 레이아웃
center_col, right_col = st.columns([5.0, 2.8], gap="large")

# 중앙: 문서 에디터
with center_col:
    render_plan_view()

# 우측: AI Assistant
with right_col:
    # 채팅 입력이 필요한 경우 or 로딩 중일 때
    if st.session_state.state['supervision']['request_type'] == "text" or st.session_state.phase in ['planning', 'form_response', 'edit']:
```
