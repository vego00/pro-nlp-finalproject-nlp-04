---
title: "PostgreSQL 테이블: sessions (LangGraph 상태 스냅샷)"
tags:
  - database
  - layer/postgres
---

# `sessions` 테이블

- **상위 문서**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **연관 테이블**: [[db__documents]], [[db__jobs]], [[db__agent_runs]]
- **사용 코드 모듈**: [[mod__storage__repository]], [[mod__web__app]], [[mod__graph__supervisor_graph]]

> 문서와 1:1로 연결되며 LangGraph `GlobalState`(메시지, 아이디어 청사진, 섹션, 질문 폼)와 실행 상태를 보관합니다.

## 컬럼 스키마

| 컬럼명 | 타입 / 제약조건 | 설명 |
|---|---|---|
| `id` | `TEXT PK` | 세션 ID (32자 hex) |
| `document_id` | `TEXT NOT NULL UNIQUE FK -> documents(id) ON DELETE CASCADE` | 연결된 문서 ID |
| `status` | `TEXT NOT NULL` | `ready` | `running` | `error` |
| `stage` | `TEXT NOT NULL` | 현재 진행 단계 (`idea_structuring` | `planning` | `research`) |
| `error` | `TEXT` | 사용자에게 표시할 오류 메시지 |
| `run_token` | `TEXT` | 현재 실행 중인 Job 토큰 |
| `state` | `JSONB NOT NULL` | 직렬화된 LangGraph `GlobalState` |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 생성 시각 |
| `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 갱신 시각 |
