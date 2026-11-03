---
title: "PostgreSQL 테이블: users (계정 · 권한)"
tags:
  - database
  - layer/postgres
---

# `users` 테이블

- **상위 문서**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **연관 테이블**: [[db__login_sessions]], [[db__documents]], [[db__jobs]]
- **사용 코드 모듈**: [[mod__storage__database]], [[mod__storage__accounts]], [[mod__web__auth]]

> 비밀번호(Argon2) 및 Google OAuth 계정, 관리자 여부(`is_admin`), 활성 상태를 저장합니다.

## 컬럼 스키마

| 컬럼명 | 타입 / 제약조건 | 설명 |
|---|---|---|
| `id` | `TEXT PK` | 사용자 고유 UUID (`local` 기본값: `00000000-0000-0000-0000-000000000001`) |
| `key` | `TEXT UNIQUE NOT NULL` | 내부 식별 키 (`local` 또는 `account:<uuid>`) |
| `email` | `TEXT UNIQUE` | 로그인 이메일 (소문자 정규화) |
| `password_hash` | `TEXT` | Argon2id 해시 문자열 |
| `google_sub` | `TEXT UNIQUE` | Google OIDC 고유 `sub` 식별자 |
| `is_admin` | `BOOLEAN NOT NULL DEFAULT false` | 관리자 여부 |
| `active` | `BOOLEAN NOT NULL DEFAULT true` | 활성 계정 여부 |
| `allow_google` | `BOOLEAN NOT NULL DEFAULT false` | Google 로그인 허용 여부 |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 생성 시각 |
