---
title: 01. 웹 대시보드 · Tiptap 에디터 계층
tags:
  - architecture
  - layer/web
---

# 01. 웹 대시보드 · Tiptap 에디터 계층 (`src/web/`)

상위 허브: [[00-Index]] | 연관 계층: [[02-Storage-and-Auth]], [[03-LangGraph-Agents]], [[04-Models-and-Config]]
운영 가이드: [[dashboard]]

## 코드 모듈 노드 (클릭 시 함수/소스 확인)

- [[mod__web__app]] (`src/web/app.py`) — FastAPI 앱, `lifespan` 초기화, 인증/CSRF 미들웨어, 세션·초안·메시지·문장 다듬기 API
- [[mod__web__auth]] (`src/web/auth.py`) — `/api/auth/*` 라우터 (비밀번호 로그인, Google OIDC, 로그아웃, 현재 사용자 확인)
- [[mod__web__history_api]] (`src/web/history_api.py`) — `/api/sessions/{id}/versions`, `/restore`, `/jobs`, `/api/jobs/{id}` 라우터
- [[mod__main]] (`src/main.py`) & [[mod__front__ui_components]] (`src/front/ui_components.py`) — 레거시 Streamlit 인터페이스

## 초안 자동 저장 · 충돌 복구 · AI 요청 흐름

```mermaid
sequenceDiagram
    participant Browser as Browser (Tiptap + app.js)
    participant FastAPI as FastAPI (src/web/app.py)
    participant Repo as Storage (repository.py / history.py)
    participant Graph as LangGraph (supervisor_app)

    Browser->>Browser: 입력 즉시 localStorage 임시 보관 (version: 3)
    Browser->>FastAPI: PUT /api/sessions/{id}/draft (base_revision)
    alt base_revision 일치
        FastAPI->>Repo: save_draft() + append_version('draft')
        Repo-->>FastAPI: draft_revision + 1
        FastAPI-->>Browser: 200 OK (최신 draft_revision)
    else 다른 탭/세션에서 먼저 수정됨
        FastAPI-->>Browser: 409 Conflict
        Browser->>Browser: 충돌 배너 표시 (최신본 열기 / 내 편집을 사본으로 저장)
    end

    Browser->>FastAPI: POST /api/sessions/{id}/messages (Idempotency-Key)
    FastAPI->>Repo: claim() (SELECT FOR UPDATE + jobs INSERT)
    FastAPI-->>Browser: 202 Accepted (job_id)
    FastAPI->>Graph: 비동기 run() -> invoke_graph(state)
    loop 1.8초 폴링
        Browser->>FastAPI: GET /api/sessions/{id}
    end
    Graph-->>FastAPI: 최종 Markdown + 상태 반환
    FastAPI->>Repo: complete() + append_version('generated')
```
