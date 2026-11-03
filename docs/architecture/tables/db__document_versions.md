---
title: "PostgreSQL 테이블: document_versions (불변 버전 이력)"
tags:
  - database
  - layer/postgres
---

# `document_versions` 테이블

- **상위 문서**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **연관 테이블**: [[db__documents]]
- **사용 코드 모듈**: [[mod__storage__history]], [[mod__web__history_api]]

> 초안 저장(`draft`) 및 AI 기획서 생성(`generated`), 이전 버전 복원(`restore`) 시마다 스냅샷을 영구 보존합니다.

## 컬럼 스키마

| 컬럼명 | 타입 / 제약조건 | 설명 |
|---|---|---|
| `id` | `BIGSERIAL PK` | 버전 일련번호 |
| `document_id` | `TEXT NOT NULL FK -> documents(id) ON DELETE CASCADE` | 대상 문서 ID |
| `kind` | `TEXT NOT NULL` | `draft` (사용자 초안) 또는 `generated` (AI 결과) |
| `revision` | `INTEGER NOT NULL` | 저장 당시의 리비전 번호 |
| `markdown` | `TEXT NOT NULL` | 버전 스냅샷 Markdown |
| `document_json` | `JSONB` | 버전 스냅샷 Tiptap JSON |
| `source` | `TEXT NOT NULL` | `create` | `save` | `copy` | `restore` | `ai` |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 기록 시각 |
