---
title: "src/prompts/edit_prompts.py"
tags:
  - code
  - layer/prompt
---

# `src/prompts/edit_prompts.py`

- **소속 계층 태그**: `#layer/prompt`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: 없음



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/prompts/edit_prompts.py`)

```python
# Edit Agent Prompts

PARTIAL_EDIT_SYSTEM_PROMPT = """당신은 전문 문서 에디터입니다.
사용자의 요청에 따라 문맥을 고려하여 문서의 일부분을 수정해야 합니다.

**작업 목표**:
1. [수정 대상 내용]을 [수정 요청]에 맞게 다시 작성하세요.
2. [앞 문맥]과 [뒷 문맥]을 고려하여 글의 흐름이 자연스럽게 이어지도록 하세요.
3. 오직 **수정된 결과물**만 출력하세요. (설명이나 인사말 제외)
4. {granularity} 단위의 수정임을 감안하여 분량을 조절하세요.

**문서 구조**
- Section: 문서의 목차에 해당하는 부분
- Paragraph: 섹션 내의 문단
- Sentence: 문단 내의 문장
"""

PARTIAL_EDIT_USER_PROMPT = """
[앞 문맥]
{prefix_text}

[수정 대상 내용]
{target_text}

[뒷 문맥]
{suffix_text}

[수정 요청]
{instruction}

수정된 내용:"""

# Section Regeneration Guideline Injection Template
SECTION_REGENERATION_GUIDELINE_TEMPLATE = """{original_guideline}

[USER REVISION REQEUST]: {instruction}{feedback_section}

(기존 기획의 톤앤매너와 양식을 유지하면서, 위 요청 사항을 자연스럽게 반영하여 섹션을 업데이트하세요.)"""
```
