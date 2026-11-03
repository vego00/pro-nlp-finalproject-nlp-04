---
title: "PostgreSQL 테이블: login_sessions (로그인 세션 · CSRF)"
tags:
  - database
  - layer/postgres
---

# `login_sessions` 테이블

- **상위 문서**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **연관 테이블**: [[db__users]]
- **사용 코드 모듈**: [[mod__web__auth]], [[mod__storage__accounts]]

> HttpOnly 쿠키(`div_login`)의 SHA-256 해시와 세션별 CSRF 토큰, 만료 시각(12시간)을 관리합니다.

## 컬럼 스키마

| 컬럼명 | 타입 / 제약조건 | 설명 |
|---|---|---|
| `token_hash` | `TEXT PK` | 세션 쿠키 토큰의 SHA-256 해시 |
| `user_id` | `TEXT NOT NULL FK -> users(id) ON DELETE CASCADE` | 소유 사용자 ID |
| `csrf` | `TEXT NOT NULL` | 상태 변경 API 검증용 `X-CSRF-Token` 값 |
| `expires_at` | `TIMESTAMPTZ NOT NULL` | 세션 만료 시각 (발급 후 12시간) |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 발급 시각 |
