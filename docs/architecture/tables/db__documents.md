---
title: "PostgreSQL 테이블: documents (문서 · 서식 초안 · 낙관적 잠금)"
tags:
  - database
  - layer/postgres
---

# `documents` 테이블

- **상위 문서**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **연관 테이블**: [[db__users]], [[db__document_versions]], [[db__sessions]]
- **사용 코드 모듈**: [[mod__storage__database]], [[mod__storage__repository]], [[mod__storage__history]]

> Tiptap JSONB 초안과 Markdown 원문, 낙관적 잠금 카운터(`draft_revision`), 최신 AI 생성 결과를 저장합니다.

## 컬럼 스키마

| 컬럼명 | 타입 / 제약조건 | 설명 |
|---|---|---|
| `id` | `TEXT PK` | 문서 UUID |
| `owner_id` | `TEXT NOT NULL FK -> users(id)` | 문서 소유자 ID (사용자 간 격리) |
| `title` | `TEXT NOT NULL` | 문서 첫 제목 또는 요약 제목 |
| `draft` | `TEXT NOT NULL` | 현재 편집 중인 초안 Markdown |
| `draft_document` | `JSONB` | Tiptap 에디터 JSON 트리 (체크리스트·표·서식 보존) |
| `draft_revision` | `INTEGER NOT NULL DEFAULT 0` | 낙관적 잠금 리비전 번호 (저장 시 1씩 증가) |
| `generated_markdown` | `TEXT NOT NULL` | LangGraph 에이전트가 생성한 최신 기획서 Markdown |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 생성 시각 |
| `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 최종 수정 시각 |
