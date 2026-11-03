---
title: "PostgreSQL 테이블: agent_runs (에이전트 실행 감사 로그)"
tags:
  - database
  - layer/postgres
---

# `agent_runs` 테이블

- **상위 문서**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **연관 테이블**: [[db__sessions]]
- **사용 코드 모듈**: [[mod__storage__repository]], [[mod__storage__database]]

> 각 LangGraph 실행 라운드의 시작·완료·중단(`interrupted`) 시각과 단계를 기록합니다.

## 컬럼 스키마

| 컬럼명 | 타입 / 제약조건 | 설명 |
|---|---|---|
| `id` | `TEXT PK` | 실행 로그 ID (`run_token`) |
| `session_id` | `TEXT NOT NULL FK -> sessions(id) ON DELETE CASCADE` | 세션 ID |
| `stage` | `TEXT NOT NULL` | 실행 단계 |
| `status` | `TEXT NOT NULL` | `running` | `completed` | `error` | `interrupted` |
| `error` | `TEXT` | 오류 메시지 |
| `started_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 시작 시각 |
| `finished_at` | `TIMESTAMPTZ` | 종료 시각 |
