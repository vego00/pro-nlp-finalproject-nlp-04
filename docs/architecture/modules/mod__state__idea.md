---
title: "src/state/idea.py"
tags:
  - code
  - layer/state
---

# `src/state/idea.py`

- **소속 계층 태그**: `#layer/state`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__state__base]]



## 정의된 클래스 / 상태 스키마
- `InternalState`

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/state/idea.py`)

```python
from state.base import GlobalState
from typing import Annotated, List

# 기존 GlobalState를 상속받습니다.
class InternalState(GlobalState):
    # 분석 노드에서 추출할 구체적인 작업 리스트
    target_sections: Annotated[List[str], 'Sections to be updated']
    # 이전 질문 내용
    required_data_points: Annotated[List[str], 'Specific points to fill']
    # Analyzer가 판단한 유저의 의도 (내부 로직 분기용)
    internal_user_intent: Annotated[str, 'Internal decision flag']
```
