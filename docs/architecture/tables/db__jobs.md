---
title: "PostgreSQL 테이블: jobs (멱등성 요청 · 비동기 Job)"
tags:
  - database
  - layer/postgres
---

# `jobs` 테이블

- **상위 문서**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **연관 테이블**: [[db__users]], [[db__sessions]]
- **사용 코드 모듈**: [[mod__storage__repository]], [[mod__storage__history]], [[mod__web__app]]

> `Idempotency-Key`와 입력 해시(`input_hash`)로 중복 AI 요청을 방지하고 비동기 실행 결과를 추적합니다.

## 컬럼 스키마

| 컬럼명 | 타입 / 제약조건 | 설명 |
|---|---|---|
| `id` | `TEXT PK` | Job UUID (`run_token`) |
| `owner_id` | `TEXT NOT NULL FK -> users(id)` | 요청 사용자 ID |
| `session_id` | `TEXT NOT NULL FK -> sessions(id) ON DELETE CASCADE` | 대상 세션 ID |
| `request_key` | `TEXT NOT NULL` | 클라이언트 `Idempotency-Key` 헤더 (owner_id와 복합 UNIQUE) |
| `input_hash` | `TEXT NOT NULL` | 요청 본문 SHA-256 해시 (키 재사용 시 본문 변조 감지) |
| `input` | `JSONB NOT NULL` | 원본 요청 페이로드 및 초안 포함 입력 |
| `kind` | `TEXT NOT NULL` | `planning` (채팅/기획) 또는 `revision` (선택 문장 다듬기) |
| `status` | `TEXT NOT NULL` | `running` | `succeeded` | `failed` | `interrupted` |
| `base_revision` | `INTEGER NOT NULL DEFAULT 0` | 요청 시작 시점의 초안 리비전 |
| `result` | `JSONB` | 완료 결과 스냅샷 |
| `error` | `TEXT` | 실패/중단 사유 |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 시작 시각 |
| `finished_at` | `TIMESTAMPTZ` | 종료 시각 |
