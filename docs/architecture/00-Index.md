---
title: DIV 아키텍처 허브 (MOC)
tags:
  - architecture
  - moc
  - doc
---

# DIV (Design In Vibe) 프로젝트 아키텍처 허브

이 폴더(`docs/architecture/`)는 **Obsidian Canvas**와 **Graph View (`Ctrl+G`)**, 그리고 **Mermaid 다이어그램**으로 `pro-nlp-finalproject-nlp-04` 전체 코드(`src/`)와 PostgreSQL 7개 테이블 구조를 시각화합니다.

## 1. 2D 캔버스 보드 바로가기 (`.canvas`)

- **[[div-architecture.canvas|전체 시스템 아키텍처 캔버스]]** — 실행 스크립트 · FastAPI/Tiptap · PostgreSQL · LangGraph · 공통 모델 5계층 한눈에 보기
- **[[langgraph-flow.canvas|LangGraph 멀티 에이전트 흐름 캔버스]]** — `Supervisor` 라우팅과 `Idea` · `Plan` · `Research` · `Visual` · `Edit` · `Evaluation` 상태 전이
- **[[storage-auth-flow.canvas|PostgreSQL 저장소 · 인증 · Job 캔버스]]** — 7개 핵심 테이블 관계와 `.env` 관리자 동기화, 낙관적 잠금, 멱등성 처리

## 2. 계층별 상세 노트 (`#layer/*`)

1. **[[01-Web-and-Editor]]** (`#layer/web`) — FastAPI 서버([[mod__web__app]]), 인증([[mod__web__auth]]), 이력([[mod__web__history_api]]), Tiptap 에디터
2. **[[02-Storage-and-Auth]]** (`#layer/postgres`) — PostgreSQL 7개 테이블([[db__users]], [[db__login_sessions]], [[db__documents]], [[db__document_versions]], [[db__sessions]], [[db__jobs]], [[db__agent_runs]]) 및 저장소 모듈([[mod__storage__repository]], [[mod__storage__history]], [[mod__storage__accounts]])
3. **[[03-LangGraph-Agents]]** (`#layer/langgraph`, `#layer/agent`) — [[mod__graph__supervisor_graph]] 및 하위 그래프·에이전트·상태 스키마 전체 연결
4. **[[04-Models-and-Config]]** (`#layer/model`) — 공통 LLM 팩토리([[mod__models__llm]], [[mod__config__config]]) 및 임베딩([[mod__models__embeddings]])

## 3. 기존 운영 · 설계 문서 연결

- [[dashboard|FastAPI + HTML 대시보드 실행 안내]]
- [[postgresql-local|로컬 PostgreSQL (Docker Desktop) 안내]]
- [[postgresql-accounts-jobs|계정 · 문서 버전 · Job 운영 안내]]
- [[ollama-docker|Docker Ollama 및 향후 Colab GPU 연결]]
- [[evaluation_agent|기획서 정량 평가 에이전트 문서]]
- [[postgresql-storage-design|PostgreSQL 저장소 설계서]]
- [[postgresql-implementation-plan|PostgreSQL 도입 계획]]
