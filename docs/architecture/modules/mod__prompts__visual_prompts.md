---
title: "src/prompts/visual_prompts.py"
tags:
  - code
  - layer/prompt
---

# `src/prompts/visual_prompts.py`

- **소속 계층 태그**: `#layer/prompt`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: 없음



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/prompts/visual_prompts.py`)

```python
# Visual Agent Prompts

TABLE_RENDER_PROMPT = """
다음 텍스트를 기반으로 '{table_type}' 스타일의 Markdown Table을 작성해줘.{feedback_text}

규칙:
- 표만 출력해. 제목(#, ##, ### 등)이나 설명 텍스트 없이 오직 표만.
- 표는 완전하고 읽기 쉽게 작성해.

내용: {text}
"""

DIAGRAM_RENDER_PROMPT = """
다음 텍스트를 기반으로 '{diagram_type}' 스타일의 Mermaid 다이어그램 코드를 작성해줘.{feedback_text}

규칙:
1. 오직 Mermaid 코드 블록만 출력해. 제목이나 설명 텍스트 없이.
2. 마크다운 코드 블록 안에 작성해.
3. **Syntax 중요**: 노드 라벨에 괄호()가 포함될 경우, 반드시 따옴표로 감싸거나(예: A["텍스트(괄호)"]) 괄호를 제거해. (Mermaid 구문 오류 방지)
4. 흐름이 논리적이고 명확해야 해.

내용: {text}
"""

CHART_DATA_EXTRACTION_PROMPT = """
다음 텍스트에서 '{chart_type}' 차트를 그리기 위한 수치 데이터를 추출해줘.
내용에 수치가 직접적으로 없더라도, 문맥상 적절한 추정치를 사용해서 차트 데이터를 만들어줘.

내용: {text_snippet}
"""
```
