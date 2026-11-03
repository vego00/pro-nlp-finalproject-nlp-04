# Obsidian 기반 프로젝트 구조 시각화 계획

## Goal Description

현재 `pro-nlp-finalproject-nlp-04` (DIV · Design In Vibe) 프로젝트는 **FastAPI + Tiptap 웹 대시보드**, **PostgreSQL 영속화/인증/버전·Job 계층**, **LangGraph 멀티 에이전트 파이프라인(Supervisor · Idea · Plan · Research · Visual · Edit · Evaluation)**, **공통 모델 팩토리(Ollama · Gemini · OpenAI · Upstage)** 로 구성되어 있습니다.

**Obsidian(옵시디언)을 바로 사용할 수 있으며**, 별도 커뮤니티 플러그인이나 외부 패키지 설치 없이 옵시디언의 기본 내장 기능 3가지를 조합해 프로젝트 아키텍처를 입체적으로 시각화합니다:

1. **Obsidian Canvas (`docs/architecture/div-architecture.canvas`)** — 오픈 스펙인 [JSON Canvas 1.0](https://jsoncanvas.org/) 파일로, 계층별 그룹 박스·모듈 카드·실제 소스 파일·문서 노드를 2D 무한 캔버스 위에 배치하고 화살표(데이터/제어 흐름)로 연결합니다.
2. **Obsidian Graph View (`[[Wikilinks]]` + `#tags`)** — `docs/architecture/` 아래에 계층별 마크다운 노트를 두고 상호 `[[위키링크]]`와 `#layer/web`, `#layer/storage`, `#layer/agent`, `#layer/model` 태그를 부여해 옵시디언 **그래프 뷰(Graph View)** 에서 노드 클러스터와 의존성을 인터랙티브하게 탐색할 수 있게 합니다.
3. **Mermaid 다이어그램 내장** — 각 노트에 Mermaid(`flowchart`, `sequenceDiagram`, `erDiagram`)를 함께 넣어, 옵시디언뿐 아니라 VS Code 미리보기와 GitHub에서도 동일하게 렌더링되도록 구성합니다.
4. **자동 갱신 스크립트 (`scripts/generate_obsidian_map.py`)** — 표준 라이브러리만 사용하는 Python 스크립트로, 코드 구조가 바뀔 때 언제든 `.canvas`와 아키텍처 노트를 다시 생성할 수 있게 합니다.

---

## User Review Required

> [!IMPORTANT]
> **Obsidian Vault(보관함) 열기 위치 선택**
> - **권장 방식 (`docs/` 폴더 또는 프로젝트 루트를 Vault로 열기)**: Windows에 설치된 Obsidian에서 `\\wsl.localhost\Ubuntu\home\p141\pro-nlp-finalproject-nlp-04\docs`(문서 전용) 또는 프로젝트 루트 전체를 **"Open folder as vault"** 로 열면 됩니다.
> - 루트 전체를 Vault로 열면 `.canvas` 안에서 `src/web/app.py` 같은 실제 코드 파일로의 링크까지 바로 클릭해 열 수 있고, 대신 `.venv/`, `node_modules/`, `.git/` 등을 옵시디언 인덱싱에서 제외하도록 `.obsidian/app.json`(`userIgnoreFilters`) 템플릿을 함께 생성해 줄 수 있습니다.
> - 개인 워크스페이스 상태가 Git에 섞이지 않도록 `.gitignore`에 `.obsidian/workspace*.json`을 추가합니다.

---

## Open Questions

1. **Vault 열기 기준**: 프로젝트 **루트 폴더**를 옵시디언 Vault로 열 예정이신가요, 아니면 **`docs/` 폴더**만 열 예정이신가요? (기본 권장: 프로젝트 루트 + `.venv`/`node_modules` 무시 설정 자동 구성)
2. **시각화 범위**: 전체 아키텍처 캔버스(`div-architecture.canvas`) 외에 **LangGraph 에이전트 상태 흐름 전용 캔버스(`langgraph-flow.canvas`)** 와 **PostgreSQL ERD/저장소 캔버스(`storage-auth-flow.canvas`)** 도 분리해서 함께 만들까요? (기본 권장: 통합 1개 + 세부 2개 모두 생성)

---

## Proposed Changes

### 1. 아키텍처 시각화 생성기 & 스크립트
- **[NEW] `scripts/generate_obsidian_map.py`**: 외부 의존성 없이 Python 표준 라이브러리(`json`, `pathlib`, `ast`)만 사용하여 `src/` 패키지의 실제 모듈/함수와 `docs/` 문서를 스캔하고 `.canvas`와 마크다운 노트를 생성·검증하는 스크립트입니다.

### 2. Obsidian Canvas 파일 (`docs/architecture/*.canvas`)
- **[NEW] `docs/architecture/div-architecture.canvas`**: 전체 5개 계층 그룹(Entry/Docker, FastAPI/Tiptap Web, PostgreSQL Storage, LangGraph Multi-Agent, Shared LLM/Config)과 데이터·호출 흐름 엣지를 배치한 메인 캔버스 보드
- **[NEW] `docs/architecture/langgraph-flow.canvas`**: `GlobalState`를 중심으로 `Supervisor` → `Idea` / `Plan` / `Research` / `Visual` / `Edit` 서브그래프의 노드 전이 조건과 상태 스키마를 시각화한 캔버스
- **[NEW] `docs/architecture/storage-auth-flow.canvas`**: PostgreSQL 7개 테이블(`users`, `login_sessions`, `documents`, `document_versions`, `sessions`, `jobs`, `agent_runs`)과 `.env` 관리자 동기화, 낙관적 잠금(`base_revision`), 멱등성 키(`Idempotency-Key`) 흐름을 시각화한 캔버스

### 3. Obsidian Graph View용 마크다운 허브 (`docs/architecture/*.md`)
- **[NEW] `docs/architecture/00-Index.md`** (아키텍처 홈 / MOC)
- **[NEW] `docs/architecture/01-Web-and-Editor.md`** (`#layer/web`)
- **[NEW] `docs/architecture/02-Storage-and-Auth.md`** (`#layer/storage`)
- **[NEW] `docs/architecture/03-LangGraph-Agents.md`** (`#layer/agent`)
- **[NEW] `docs/architecture/04-Models-and-Config.md`** (`#layer/model`)

### 4. Obsidian Vault 설정 및 Git 제외 규칙
- **[NEW] `.obsidian/app.json` & `.obsidian/graph.json`**: `.venv/`, `node_modules/`, `qdrant_data/`, `output/`, `logs/`, `__pycache__/` 인덱싱 자동 제외 및 그래프 뷰 태그별 색상 구분 설정
- **[MODIFY] `.gitignore`**: `.obsidian/workspace*.json` 제외

