---
title: "src/front/ui_components.py"
tags:
  - code
  - layer/web
---

# `src/front/ui_components.py`

- **소속 계층 태그**: `#layer/web`
- **상위 아키텍처 노트**: [[00-Index]], [[01-Web-and-Editor]]
- **내부 모듈 의존성(Imports)**: [[mod__graph__supervisor_graph]]



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def init_page()`
- `def render_question_view(questions)`
- `def st_mermaid(code)`
- `def extract_heading_line_map(markdown)`
- `def _render_text_and_images(text)`
- `def render_heading(level, text, key)`
- `def _render_text_images_and_headings(text, h1_key_idx, h2_key_idx)`
- `def parse_markdown_blocks(markdown_string)`
- `def st_markdown(markdown_string)`
- `def render_plan_view()`

## 소스 코드 미리보기 (`src/front/ui_components.py`)

```python
import streamlit as st
from graph.supervisor_graph import supervisor_app
from pathlib import Path
import re
import streamlit.components.v1 as components

def init_page():
    # 페이지 설정
    st.set_page_config(page_title="Vibe Planner", layout="wide")

    # --- 커스텀 CSS 수정 버전 ---
    st.markdown("""
        <style>
        .stApp {
            height: 100vh;
            overflow: hidden;
        }
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        /* 헤더 전체를 투명하게 만들고 높이 조절 */
        header {
            background-color: rgba(0,0,0,0) !important;
            border-bottom: none !important;
        }

        /* 사이드바 열기/닫기 버튼 위치 및 스타일 조정 (선택 사항) */
        /* 버튼이 너무 위에 붙어 있다면 top 값을 조절하세요 */
        [data-testid="stSidebarCollapseButton"] {
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-top: 10px;
        }

        /* 배경 및 레이아웃 설정 (이전과 동일) */
        .stApp {
            background-color: #f0f2f5;
        }
        
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e5e7eb;
        }
        /* 캔버스 컨테이너 스타일 */
        .canvas-container {
            background-color: white;
            padding: 60px 80px; /* 실제 종이 여백 느낌 */
            border-radius: 4px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border: 1px solid #E5E7EB;
            
            /* --- 스크롤 핵심 설정 --- */
            height: calc(100vh - 100px); /* 헤더 등을 제외한 나머지 높이 전부 사용 */
            overflow-y: auto;       /* 내용이 많아지면 내부 스크롤 발생 */
            
            color: #1F2937;
            line-height: 1.8;
            word-break: keep-all;   /* 한글 줄바꿈 최적화 */
        }
        /* 스크롤바 디자인 (크롬/사파리) - 선택 사항 */
        .canvas-container::-webkit-scrollbar {
            width: 6px;
        }
        .canvas-container::-webkit-scrollbar-thumb {
            background-color: #d1d5db;
            border-radius: 10px;
        }
        .canvas-container::-webkit-scrollbar-track {
            background-color: #f9fafb;
        }
        /* 캔버스 내부 마크다운 텍스트 스타일 강제 적용 */
        .canvas-container h1, .canvas-container h2, .canvas-container h3 {
            color: #111827 !important;
            border-bottom: 2px solid #F3F4F6;
            padding-bottom: 8px;
            margin-top: 1.5em;
        }
        .canvas-container p, .canvas-container li {
            font-size: 1.05rem;
            line-height: 1.8;
            color: #374151;
        }
        /* 채팅 입력창 전체 영역 스타일 */
        [data-testid="stChatInput"] {
            border: 1px solid #D1D5DB !important; /* 채팅창 컨테이너와 동일한 선 */
```
