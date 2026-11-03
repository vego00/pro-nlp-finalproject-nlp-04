---
title: "src/graph/research_graph.py"
tags:
  - code
  - layer/langgraph
---

# `src/graph/research_graph.py`

- **소속 계층 태그**: `#layer/langgraph`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__research]], [[mod__state__base]], [[mod__state__research]]



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def check_analyst(state)`
- `def run_research_for_plan(state)`

## 소스 코드 미리보기 (`src/graph/research_graph.py`)

```python
from langgraph.graph import StateGraph, END
from state.base import GlobalState
from state.research import ResearchState
from agents.research import research_generate, research_evaluate, research_eval_router
from agents.research import generate_queries, search_with_tavily, analysis_search_results, upsert_qdrant, execute_hybrid_search


# # 노드 설정
# research_graph = StateGraph(GlobalState)
# research_graph.add_node("generate", research_generate)
# research_graph.add_node("evaluate", research_evaluate)
# research_graph.set_entry_point("generate")

# # 엣지 설정
# research_graph.add_edge("generate", "evaluate")
# research_graph.add_conditional_edges(
#     "evaluate",
#     research_eval_router,
#     {
#         "pass": END,
#         "retry": "generate"
#     }
# )

def check_analyst(state: ResearchState):
    if state.is_analysis_need == True:
        return "analysis"
    else:
        return END

research_graph = StateGraph(ResearchState)

research_graph.add_node("query_gen", generate_queries)
research_graph.add_node("search", search_with_tavily)
research_graph.add_node("upsert_qdrant", upsert_qdrant)
research_graph.add_node("hybrid_search", execute_hybrid_search)
research_graph.add_node("analysis", analysis_search_results)

research_graph.set_entry_point("query_gen")
research_graph.add_edge("query_gen", "search")
research_graph.add_edge("search", "upsert_qdrant")
research_graph.add_edge("upsert_qdrant", "hybrid_search")
research_graph.add_conditional_edges(
    "hybrid_search",
    check_analyst,
    {"analysis": "analysis", END: END})
research_graph.add_edge("analysis", END)

# 컴파일
research_subgraph = research_graph.compile()


# =====================================================
# [Plan Agent 연동용] Research 서브그래프 실행 래퍼
# 
# 사용 시점:
#   - Supervisor가 RUN_RESEARCH로 라우팅했을 때 호출
#   - Plan Agent의 generate_section_node()에서 needs_research=True로 설정된 후
#
# 입력:
#   - state['research']['queries']: Plan Agent가 요청한 검색 쿼리 목록
#   - state['research']['section_context']: 리서치 대상 섹션 제목
#
# 출력:
#   - state['research']['gathered_evidence']: 수집된 검색 결과 리스트
#   - state['research']['analysis_result']: 분석 결과 텍스트
#   - state['research']['needs_research']: False로 설정
# =====================================================
def run_research_for_plan(state: dict) -> dict:
    """
    GlobalState를 받아서 Research 서브그래프를 실행하고,
    결과를 state['research']에 저장하여 반환
    """
    research_info = state.get('research', {})
    queries = research_info.get('queries', [])
    section_context = research_info.get('section_context', '')
    
    if not queries and not section_context:
        # 쿼리와 컨텍스트 모두 없으면 리서치 완료로 처리
        state['research'] = {
            **research_info,
            'needs_research': False,
            'evidence_store': [],
            'analysis_result': ''
        }
        return state
    
    # ResearchState 형태로 변환하여 서브그래프 실행
    # - question: 섹션 컨텍스트 (분석 시 참고) -> [Improvement] 쿼리에 리서치 목표가 있으면 그것을 질문으로 사용
    # - search_queries: Plan Agent가 제안한 쿼리들
```
