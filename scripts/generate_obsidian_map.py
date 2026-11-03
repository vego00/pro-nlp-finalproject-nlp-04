#!/usr/bin/env python3
"""Generate Obsidian Canvas boards (.canvas), Graph View Markdown notes (including
per-module LangGraph/FastAPI code nodes and per-table PostgreSQL ERD nodes),
and sync everything to the Windows-accessible Vault at C:\\Users\\141\\div-obsidian-vault.

Standard library only (ast, json, pathlib, shutil).
Run from repository root:
    .venv/bin/python scripts/generate_obsidian_map.py
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
ARCH_DIR = ROOT / "docs" / "architecture"
CODE_NOTES_DIR = ARCH_DIR / "modules"
DB_NOTES_DIR = ARCH_DIR / "tables"
OBSIDIAN_DIR = ROOT / ".obsidian"
WINDOWS_VAULT_DEFAULT = Path("/mnt/c/Users/141/div-obsidian-vault")


def group_node(node_id: str, label: str, x: int, y: int, w: int, h: int, color: str) -> dict:
    return {
        "id": node_id,
        "type": "group",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "label": label,
        "color": color,
    }


def text_node(node_id: str, text: str, x: int, y: int, w: int, h: int, color: str | None = None) -> dict:
    node = {
        "id": node_id,
        "type": "text",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "text": text,
    }
    if color:
        node["color"] = color
    return node


def file_node(node_id: str, rel_path: str, x: int, y: int, w: int, h: int, color: str | None = None) -> dict:
    node = {
        "id": node_id,
        "type": "file",
        "file": rel_path,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
    }
    if color:
        node["color"] = color
    return node


def edge(
    edge_id: str,
    from_node: str,
    to_node: str,
    label: str = "",
    from_side: str = "bottom",
    to_side: str = "top",
    color: str | None = None,
) -> dict:
    item = {
        "id": edge_id,
        "fromNode": from_node,
        "fromSide": from_side,
        "toNode": to_node,
        "toSide": to_side,
    }
    if label:
        item["label"] = label
    if color:
        item["color"] = color
    return item


def validate_canvas(name: str, data: dict) -> None:
    node_ids = {n["id"] for n in data["nodes"]}
    assert len(node_ids) == len(data["nodes"]), f"{name}: duplicate node IDs found"
    for n in data["nodes"]:
        if n["type"] == "file":
            target = ROOT / n["file"]
            assert target.exists(), f"{name}: referenced file does not exist: {n['file']}"
    for e in data["edges"]:
        assert e["fromNode"] in node_ids, f"{name}: unknown fromNode {e['fromNode']}"
        assert e["toNode"] in node_ids, f"{name}: unknown toNode {e['toNode']}"


# ---------------------------------------------------------------------------
# AST-based introspection of every Python module in src/ and migrations/
# ---------------------------------------------------------------------------

LAYER_TAGS = {
    "graph": "layer/langgraph",
    "agents": "layer/agent",
    "state": "layer/state",
    "prompts": "layer/prompt",
    "storage": "layer/postgres",
    "web": "layer/web",
    "models": "layer/model",
    "config": "layer/model",
    "front": "layer/web",
    "migrations": "layer/postgres",
}


def note_name_for_path(rel_path: Path) -> str:
    """Convert e.g. src/graph/supervisor_graph.py -> mod__graph__supervisor_graph."""
    parts = list(rel_path.with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    return "mod__" + "__".join(parts)


def collect_python_modules() -> dict[str, dict]:
    """Scan src/ and migrations/ and extract docstrings, classes, functions, and internal imports."""
    modules: dict[str, dict] = {}
    py_files: list[Path] = []
    for base in (ROOT / "src", ROOT / "migrations"):
        if base.is_dir():
            py_files.extend(sorted(base.rglob("*.py")))

    # Map importable module dotted names to note names
    dotted_to_note: dict[str, str] = {}
    for path in py_files:
        if "__pycache__" in path.parts or path.name == "__init__.py":
            continue
        rel = path.relative_to(ROOT)
        note_name = note_name_for_path(rel)
        if rel.parts[0] == "src":
            dotted = ".".join(rel.with_suffix("").parts[1:])
        else:
            dotted = ".".join(rel.with_suffix("").parts)
        dotted_to_note[dotted] = note_name
        modules[note_name] = {
            "rel_path": rel.as_posix(),
            "dotted": dotted,
            "path": path,
            "note_name": note_name,
        }

    for note_name, info in modules.items():
        source = info["path"].read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            tree = ast.Module(body=[], type_ignores=[])

        doc = ast.get_docstring(tree) or ""
        classes: list[str] = []
        functions: list[str] = []
        imports: set[str] = set()

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
                args = [a.arg for a in node.args.args]
                functions.append(f"`{prefix}{node.name}({', '.join(args)})`")

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if mod in dotted_to_note:
                    imports.add(dotted_to_note[mod])
                for alias in node.names:
                    candidate = f"{mod}.{alias.name}"
                    if candidate in dotted_to_note:
                        imports.add(dotted_to_note[candidate])
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in dotted_to_note:
                        imports.add(dotted_to_note[alias.name])

        imports.discard(note_name)
        top_pkg = info["dotted"].split(".")[0]
        info["tag"] = LAYER_TAGS.get(top_pkg, "layer/code")
        info["doc"] = doc.strip().splitlines()[0] if doc.strip() else ""
        info["classes"] = classes
        info["functions"] = functions
        info["imports"] = sorted(imports)
        info["source_preview"] = "\n".join(source.splitlines()[:90])

    return modules


POSTGRES_TABLES: dict[str, dict] = {
    "db__users": {
        "table": "users",
        "title": "PostgreSQL 테이블: users (계정 · 권한)",
        "summary": "비밀번호(Argon2) 및 Google OAuth 계정, 관리자 여부(`is_admin`), 활성 상태를 저장합니다.",
        "columns": [
            ("id", "TEXT PK", "사용자 고유 UUID (`local` 기본값: `00000000-0000-0000-0000-000000000001`)"),
            ("key", "TEXT UNIQUE NOT NULL", "내부 식별 키 (`local` 또는 `account:<uuid>`)"),
            ("email", "TEXT UNIQUE", "로그인 이메일 (소문자 정규화)"),
            ("password_hash", "TEXT", "Argon2id 해시 문자열"),
            ("google_sub", "TEXT UNIQUE", "Google OIDC 고유 `sub` 식별자"),
            ("is_admin", "BOOLEAN NOT NULL DEFAULT false", "관리자 여부"),
            ("active", "BOOLEAN NOT NULL DEFAULT true", "활성 계정 여부"),
            ("allow_google", "BOOLEAN NOT NULL DEFAULT false", "Google 로그인 허용 여부"),
            ("created_at", "TIMESTAMPTZ NOT NULL DEFAULT now()", "생성 시각"),
        ],
        "relations": ["[[db__login_sessions]]", "[[db__documents]]", "[[db__jobs]]"],
        "modules": ["[[mod__storage__database]]", "[[mod__storage__accounts]]", "[[mod__web__auth]]"],
    },
    "db__login_sessions": {
        "table": "login_sessions",
        "title": "PostgreSQL 테이블: login_sessions (로그인 세션 · CSRF)",
        "summary": "HttpOnly 쿠키(`div_login`)의 SHA-256 해시와 세션별 CSRF 토큰, 만료 시각(12시간)을 관리합니다.",
        "columns": [
            ("token_hash", "TEXT PK", "세션 쿠키 토큰의 SHA-256 해시"),
            ("user_id", "TEXT NOT NULL FK -> users(id) ON DELETE CASCADE", "소유 사용자 ID"),
            ("csrf", "TEXT NOT NULL", "상태 변경 API 검증용 `X-CSRF-Token` 값"),
            ("expires_at", "TIMESTAMPTZ NOT NULL", "세션 만료 시각 (발급 후 12시간)"),
            ("created_at", "TIMESTAMPTZ NOT NULL DEFAULT now()", "발급 시각"),
        ],
        "relations": ["[[db__users]]"],
        "modules": ["[[mod__web__auth]]", "[[mod__storage__accounts]]"],
    },
    "db__documents": {
        "table": "documents",
        "title": "PostgreSQL 테이블: documents (문서 · 서식 초안 · 낙관적 잠금)",
        "summary": "Tiptap JSONB 초안과 Markdown 원문, 낙관적 잠금 카운터(`draft_revision`), 최신 AI 생성 결과를 저장합니다.",
        "columns": [
            ("id", "TEXT PK", "문서 UUID"),
            ("owner_id", "TEXT NOT NULL FK -> users(id)", "문서 소유자 ID (사용자 간 격리)"),
            ("title", "TEXT NOT NULL", "문서 첫 제목 또는 요약 제목"),
            ("draft", "TEXT NOT NULL", "현재 편집 중인 초안 Markdown"),
            ("draft_document", "JSONB", "Tiptap 에디터 JSON 트리 (체크리스트·표·서식 보존)"),
            ("draft_revision", "INTEGER NOT NULL DEFAULT 0", "낙관적 잠금 리비전 번호 (저장 시 1씩 증가)"),
            ("generated_markdown", "TEXT NOT NULL", "LangGraph 에이전트가 생성한 최신 기획서 Markdown"),
            ("created_at", "TIMESTAMPTZ NOT NULL DEFAULT now()", "생성 시각"),
            ("updated_at", "TIMESTAMPTZ NOT NULL DEFAULT now()", "최종 수정 시각"),
        ],
        "relations": ["[[db__users]]", "[[db__document_versions]]", "[[db__sessions]]"],
        "modules": ["[[mod__storage__database]]", "[[mod__storage__repository]]", "[[mod__storage__history]]"],
    },
    "db__document_versions": {
        "table": "document_versions",
        "title": "PostgreSQL 테이블: document_versions (불변 버전 이력)",
        "summary": "초안 저장(`draft`) 및 AI 기획서 생성(`generated`), 이전 버전 복원(`restore`) 시마다 스냅샷을 영구 보존합니다.",
        "columns": [
            ("id", "BIGSERIAL PK", "버전 일련번호"),
            ("document_id", "TEXT NOT NULL FK -> documents(id) ON DELETE CASCADE", "대상 문서 ID"),
            ("kind", "TEXT NOT NULL", "`draft` (사용자 초안) 또는 `generated` (AI 결과)"),
            ("revision", "INTEGER NOT NULL", "저장 당시의 리비전 번호"),
            ("markdown", "TEXT NOT NULL", "버전 스냅샷 Markdown"),
            ("document_json", "JSONB", "버전 스냅샷 Tiptap JSON"),
            ("source", "TEXT NOT NULL", "`create` | `save` | `copy` | `restore` | `ai`"),
            ("created_at", "TIMESTAMPTZ NOT NULL DEFAULT now()", "기록 시각"),
        ],
        "relations": ["[[db__documents]]"],
        "modules": ["[[mod__storage__history]]", "[[mod__web__history_api]]"],
    },
    "db__sessions": {
        "table": "sessions",
        "title": "PostgreSQL 테이블: sessions (LangGraph 상태 스냅샷)",
        "summary": "문서와 1:1로 연결되며 LangGraph `GlobalState`(메시지, 아이디어 청사진, 섹션, 질문 폼)와 실행 상태를 보관합니다.",
        "columns": [
            ("id", "TEXT PK", "세션 ID (32자 hex)"),
            ("document_id", "TEXT NOT NULL UNIQUE FK -> documents(id) ON DELETE CASCADE", "연결된 문서 ID"),
            ("status", "TEXT NOT NULL", "`ready` | `running` | `error`"),
            ("stage", "TEXT NOT NULL", "현재 진행 단계 (`idea_structuring` | `planning` | `research`)"),
            ("error", "TEXT", "사용자에게 표시할 오류 메시지"),
            ("run_token", "TEXT", "현재 실행 중인 Job 토큰"),
            ("state", "JSONB NOT NULL", "직렬화된 LangGraph `GlobalState`"),
            ("created_at", "TIMESTAMPTZ NOT NULL DEFAULT now()", "생성 시각"),
            ("updated_at", "TIMESTAMPTZ NOT NULL DEFAULT now()", "갱신 시각"),
        ],
        "relations": ["[[db__documents]]", "[[db__jobs]]", "[[db__agent_runs]]"],
        "modules": ["[[mod__storage__repository]]", "[[mod__web__app]]", "[[mod__graph__supervisor_graph]]"],
    },
    "db__jobs": {
        "table": "jobs",
        "title": "PostgreSQL 테이블: jobs (멱등성 요청 · 비동기 Job)",
        "summary": "`Idempotency-Key`와 입력 해시(`input_hash`)로 중복 AI 요청을 방지하고 비동기 실행 결과를 추적합니다.",
        "columns": [
            ("id", "TEXT PK", "Job UUID (`run_token`)"),
            ("owner_id", "TEXT NOT NULL FK -> users(id)", "요청 사용자 ID"),
            ("session_id", "TEXT NOT NULL FK -> sessions(id) ON DELETE CASCADE", "대상 세션 ID"),
            ("request_key", "TEXT NOT NULL", "클라이언트 `Idempotency-Key` 헤더 (owner_id와 복합 UNIQUE)"),
            ("input_hash", "TEXT NOT NULL", "요청 본문 SHA-256 해시 (키 재사용 시 본문 변조 감지)"),
            ("input", "JSONB NOT NULL", "원본 요청 페이로드 및 초안 포함 입력"),
            ("kind", "TEXT NOT NULL", "`planning` (채팅/기획) 또는 `revision` (선택 문장 다듬기)"),
            ("status", "TEXT NOT NULL", "`running` | `succeeded` | `failed` | `interrupted`"),
            ("base_revision", "INTEGER NOT NULL DEFAULT 0", "요청 시작 시점의 초안 리비전"),
            ("result", "JSONB", "완료 결과 스냅샷"),
            ("error", "TEXT", "실패/중단 사유"),
            ("created_at", "TIMESTAMPTZ NOT NULL DEFAULT now()", "시작 시각"),
            ("finished_at", "TIMESTAMPTZ", "종료 시각"),
        ],
        "relations": ["[[db__users]]", "[[db__sessions]]"],
        "modules": ["[[mod__storage__repository]]", "[[mod__storage__history]]", "[[mod__web__app]]"],
    },
    "db__agent_runs": {
        "table": "agent_runs",
        "title": "PostgreSQL 테이블: agent_runs (에이전트 실행 감사 로그)",
        "summary": "각 LangGraph 실행 라운드의 시작·완료·중단(`interrupted`) 시각과 단계를 기록합니다.",
        "columns": [
            ("id", "TEXT PK", "실행 로그 ID (`run_token`)"),
            ("session_id", "TEXT NOT NULL FK -> sessions(id) ON DELETE CASCADE", "세션 ID"),
            ("stage", "TEXT NOT NULL", "실행 단계"),
            ("status", "TEXT NOT NULL", "`running` | `completed` | `error` | `interrupted`"),
            ("error", "TEXT", "오류 메시지"),
            ("started_at", "TIMESTAMPTZ NOT NULL DEFAULT now()", "시작 시각"),
            ("finished_at", "TIMESTAMPTZ", "종료 시각"),
        ],
        "relations": ["[[db__sessions]]"],
        "modules": ["[[mod__storage__repository]]", "[[mod__storage__database]]"],
    },
}


def generate_module_notes(modules: dict[str, dict]) -> None:
    CODE_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    for note_name, info in modules.items():
        imports_links = ", ".join(f"[[{imp}]]" for imp in info["imports"]) if info["imports"] else "없음"
        classes_md = "\n".join(f"- `{cls}`" for cls in info["classes"]) if info["classes"] else "- 없음"
        funcs_md = "\n".join(f"- {fn}" for fn in info["functions"]) if info["functions"] else "- 없음"

        hub_link = "[[00-Index]]"
        if info["tag"] == "layer/langgraph" or info["tag"] == "layer/agent" or info["tag"] == "layer/state" or info["tag"] == "layer/prompt":
            hub_link += ", [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]"
        elif info["tag"] == "layer/postgres":
            hub_link += ", [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]"
        elif info["tag"] == "layer/web":
            hub_link += ", [[01-Web-and-Editor]]"
        elif info["tag"] == "layer/model":
            hub_link += ", [[04-Models-and-Config]]"

        content = f"""---
title: "{info['rel_path']}"
tags:
  - code
  - {info['tag']}
---

# `{info['rel_path']}`

- **소속 계층 태그**: `#{info['tag']}`
- **상위 아키텍처 노트**: {hub_link}
- **내부 모듈 의존성(Imports)**: {imports_links}

{f"> {info['doc']}" if info['doc'] else ""}

## 정의된 클래스 / 상태 스키마
{classes_md}

## 정의된 함수 / 노드
{funcs_md}

## 소스 코드 미리보기 (`{info['rel_path']}`)

```python
{info['source_preview']}
```
"""
        (CODE_NOTES_DIR / f"{note_name}.md").write_text(content, encoding="utf-8")


def generate_table_notes() -> None:
    DB_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    for note_name, info in POSTGRES_TABLES.items():
        rows = "\n".join(f"| `{col}` | `{dtype}` | {desc} |" for col, dtype, desc in info["columns"])
        rels = ", ".join(info["relations"])
        mods = ", ".join(info["modules"])
        content = f"""---
title: "{info['title']}"
tags:
  - database
  - layer/postgres
---

# `{info['table']}` 테이블

- **상위 문서**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **연관 테이블**: {rels}
- **사용 코드 모듈**: {mods}

> {info['summary']}

## 컬럼 스키마

| 컬럼명 | 타입 / 제약조건 | 설명 |
|---|---|---|
{rows}
"""
        (DB_NOTES_DIR / f"{note_name}.md").write_text(content, encoding="utf-8")


def build_div_architecture_canvas() -> dict:
    nodes = [
        group_node("grp-entry", "1. 실행 · 운영 엔트리 (scripts/ & compose.yaml)", -920, -560, 1840, 220, "5"),
        group_node("grp-web", "2. 웹 대시보드 · 에디터 계층 (src/web/)", -920, -290, 1840, 310, "4"),
        group_node("grp-storage", "3. PostgreSQL 영속화 · 계정 · 버전 · Job 계층 (src/storage/)", -920, 70, 880, 420, "2"),
        group_node("grp-agents", "4. LangGraph 멀티 에이전트 파이프라인 (src/graph/ & src/agents/)", 0, 70, 920, 420, "6"),
        group_node("grp-models", "5. 공통 모델 팩토리 · 설정 · 인프라 (src/models/ & src/config/)", -920, 540, 1840, 260, "3"),

        text_node(
            "entry-run",
            "### `scripts/run.sh` & `run-desktop.sh`\n"
            "- `.env` / `ADMIN_*` 검증\n"
            "- `docker compose up -d --wait`\n"
            "- `alembic upgrade head`\n"
            "- 단일 프로세스 `uvicorn` 기동 (`--open`)\n"
            "- 문서: [[dashboard]]",
            -890, -510, 560, 150, "5",
        ),
        text_node(
            "entry-compose",
            "### `compose.yaml` (Docker Desktop)\n"
            "- `postgres:17-bookworm` (`127.0.0.1:5432`)\n"
            "- `ollama/ollama` (`127.0.0.1:11434`)\n"
            "- 볼륨: `postgres_data`, `ollama_data`\n"
            "- 문서: [[postgresql-local]], [[ollama-docker]]",
            -280, -510, 560, 150, "5",
        ),
        text_node(
            "entry-colab",
            "### `scripts/colab-tunnel.sh` & Colab 노트북\n"
            "- 원격 GPU Ollama SSH 포트포워딩 (`11435`)\n"
            "- `notebooks/colab_pipeline_smoke.ipynb`\n"
            "- 세부 캔버스: [[langgraph-flow.canvas]]",
            330, -510, 560, 150, "5",
        ),

        text_node(
            "web-tiptap",
            "### 브라우저 UI + Tiptap 에디터\n"
            "- `src/web/static/index.html`, `app.js`\n"
            "- `src/web/editor/editor.js` → `editor.bundle.js`\n"
            "- 실시간 임시저장(`localStorage`) + 1.2초 서버 자동저장\n"
            "- 선택 문장 AI 다듬기 (`/revise`), 버전·실행 이력 모달\n"
            "- 상세: [[01-Web-and-Editor]]",
            -890, -240, 560, 230, "4",
        ),
        text_node(
            "web-app",
            "### FastAPI 메인 서버 ([[mod__web__app]])\n"
            "- `lifespan`: `AUTH_SECRET` 확인, `store.initialize()`, `sync_admin_from_env()`\n"
            "- 세션/초안 API: `/api/sessions`, `/draft`, `/copy`, `/messages`, `/revise`\n"
            "- 상태 API: `/api/config` (`MODEL_PRESETS`), `/api/health`\n"
            "- `run_lock`으로 에이전트 그래프 단일 실행 직렬화",
            -280, -240, 580, 230, "4",
        ),
        text_node(
            "web-auth-hist",
            "### 인증 · 이력 라우터 ([[mod__web__auth]], [[mod__web__history_api]])\n"
            "- `auth.py`: Argon2 비밀번호 로그인, Google OAuth(OIDC+PKCE), HttpOnly 세션 쿠키, CSRF 검증\n"
            "- `history_api.py`: 문서 버전 조회/복원 (`/versions`), Job 조회 (`/api/jobs/{id}`)\n"
            "- 상세: [[02-Storage-and-Auth]]",
            350, -240, 540, 230, "4",
        ),

        text_node(
            "store-repo",
            "### [[mod__storage__repository]]\n"
            "- 세션/문서 CRUD 및 소유자 격리 (`owner_id()`)\n"
            "- 낙관적 잠금 (`base_revision` 비교 후 `409 Conflict`)\n"
            "- `claim()`: `SELECT ... FOR UPDATE` + Job 생성\n"
            "- 재시작 시 미완료 `running` 작업을 `interrupted`로 복구",
            -890, 120, 410, 180, "2",
        ),
        text_node(
            "store-history",
            "### [[mod__storage__history]] & [[mod__storage__accounts]]\n"
            "- `append_version()`: 모든 저장/AI 생성/복원 버전 보존\n"
            "- `existing_job()`: `Idempotency-Key` + 입력 해시 검증\n"
            "- `sync_admin_from_env()`: `.env`의 `ADMIN_EMAIL`/`ADMIN_PASSWORD` 동기화",
            -450, 120, 380, 180, "2",
        ),
        text_node(
            "store-db",
            "### [[mod__storage__database]] & PostgreSQL 7 테이블\n"
            "- [[db__users]], [[db__login_sessions]], [[db__documents]], [[db__document_versions]]\n"
            "- [[db__sessions]], [[db__jobs]], [[db__agent_runs]]\n"
            "- 세부 ERD 캔버스: [[storage-auth-flow.canvas]]",
            -890, 320, 820, 150, "2",
        ),

        text_node(
            "agent-supervisor",
            "### [[mod__graph__supervisor_graph]] ([[mod__agents__supervisor]])\n"
            "- 엔트리 노드: `supervisor` → `supervisor_router`\n"
            "- 라우팅: `ASK_USER` | `RUN_IDEA_STRUCTURING` | `RUN_PLANNING` | `RUN_RESEARCH` | `RUN_EDIT` | `Refresh`\n"
            "- 공유 상태: `GlobalState` ([[mod__state__base]])\n"
            "- 상세: [[03-LangGraph-Agents]] | 세부 캔버스: [[langgraph-flow.canvas]]",
            30, 120, 860, 160, "6",
        ),
        text_node(
            "agent-subgraphs",
            "### 전문 서브그래프 (`src/graph/*_graph.py` & `src/agents/`)\n"
            "- **Idea**: [[mod__graph__idea_graph]] → [[mod__agents__idea]]\n"
            "- **Plan**: [[mod__graph__plan_graph]] → [[mod__agents__plan_core__pipeline]]\n"
            "- **Research**: [[mod__graph__research_graph]] → [[mod__agents__research]]\n"
            "- **Visual**: [[mod__graph__visual_graph]] → [[mod__agents__visual_core__generator]]\n"
            "- **Edit / Eval**: [[mod__graph__edit_graph]], [[mod__graph__evaluation_graph]]",
            30, 300, 860, 170, "6",
        ),

        text_node(
            "model-config",
            "### [[mod__config__config]] (`.env` 우선)\n"
            "- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_MINI_MODEL`\n"
            "- `MODEL_PRESETS` (`ollama`, `openai`, `gemini`)\n"
            "- `DATABASE_URL`, `AUTH_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`\n"
            "- 상세: [[04-Models-and-Config]]",
            -890, 590, 560, 180, "3",
        ),
        text_node(
            "model-llm",
            "### [[mod__models__llm]] (`get_llm` / `get_mini_llm`)\n"
            "- **Ollama**: `qwen3.5:4b` (기본), `qwen3.8:27b` (`Qwen/Qwen3.8-27B`)\n"
            "- **Gemini**: `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.5-flash-lite`\n"
            "- **OpenAI / vLLM**: `Qwen/Qwen3.8-27B` 및 OpenAI 모델\n"
            "- **Upstage**: Solar 시리즈",
            -280, 590, 580, 180, "3",
        ),
        text_node(
            "model-emb",
            "### [[mod__models__embeddings]] · 벡터 · 외부 검색\n"
            "- FastEmbed CPU (`intfloat/multilingual-e5-small`)\n"
            "- Qdrant 로컬 저장소 (`qdrant_data/`)\n"
            "- 웹 검색: `ddgs` (기본) / `Tavily`",
            350, 590, 540, 180, "3",
        ),
    ]

    edges = [
        edge("e-run-compose", "entry-run", "entry-compose", "기동/상태 확인", "right", "left", "5"),
        edge("e-run-app", "entry-run", "web-app", "uvicorn 실행", "bottom", "top", "5"),
        edge("e-ui-app", "web-tiptap", "web-app", "REST + CSRF + Idempotency-Key", "right", "left", "4"),
        edge("e-app-auth", "web-app", "web-auth-hist", "인증 미들웨어 · 라우터", "right", "left", "4"),
        edge("e-app-repo", "web-app", "store-repo", "세션·초안·Job 트랜잭션", "bottom", "top", "2"),
        edge("e-auth-hist", "web-auth-hist", "store-history", "버전·Job·관리자 동기화", "bottom", "top", "2"),
        edge("e-repo-db", "store-repo", "store-db", "SQLAlchemy Async", "bottom", "top", "2"),
        edge("e-hist-db", "store-history", "store-db", "SQLAlchemy Async", "bottom", "top", "2"),
        edge("e-app-sup", "web-app", "agent-supervisor", "invoke_graph(state)", "bottom", "top", "6"),
        edge("e-sup-sub", "agent-supervisor", "agent-subgraphs", "조건부 라우팅 · 상태 전이", "bottom", "top", "6"),
        edge("e-sub-llm", "agent-subgraphs", "model-llm", "get_llm() / get_mini_llm()", "bottom", "top", "3"),
        edge("e-sub-emb", "agent-subgraphs", "model-emb", "RAG · 웹 리서치", "bottom", "top", "3"),
        edge("e-llm-cfg", "model-llm", "model-config", "설정 참조", "left", "right", "3"),
    ]
    return {"nodes": nodes, "edges": edges}


def build_langgraph_flow_canvas() -> dict:
    nodes = [
        group_node("lg-grp-state", "공유 상태 스키마 (src/state/)", -860, -480, 1720, 190, "3"),
        group_node("lg-grp-core", "Supervisor 오케스트레이션 및 서브그래프 (src/graph/ & src/agents/)", -860, -250, 1720, 620, "6"),
        group_node("lg-grp-eval", "독립 정량 평가 파이프라인 (src/evaluate.py)", -860, 410, 1720, 190, "5"),

        text_node(
            "lg-state",
            "### `GlobalState` ([[mod__state__base]])\n"
            "- `messages`: 대화 이력 (`HumanMessage`, `AIMessage`)\n"
            "- `idea` ([[mod__state__idea]]): `planning_style`, `rationale`, `toc`, `blueprint`\n"
            "- `plan` ([[mod__state__plan]]): `sections`, `final_markdown`, `visual_artifacts`\n"
            "- `supervision`: `last_decision`, `request_type` (`text` | `idea_form`), `edit_request` ([[mod__state__edit]])\n"
            "- `research` ([[mod__state__research]]) & `visual` ([[mod__state__visual]])",
            -830, -435, 1660, 130, "3",
        ),
        text_node(
            "lg-supervisor",
            "### `supervisor_node` & `supervisor_router`\n"
            "- 그래프: [[mod__graph__supervisor_graph]] | 에이전트: [[mod__agents__supervisor]] | 프롬프트: [[mod__prompts__supervisor_prompt]]\n"
            "- 사용자 입력과 현재 `idea`/`plan` 진행도를 분석해 다음 실행 단계를 결정\n"
            "- `Refresh` 반환 시 대시보드 백그라운드 작업이 자동으로 다음 라운드를 재호출 (`GRAPH_MAX_ROUNDS=30`)",
            -360, -200, 720, 140, "6",
        ),
        text_node(
            "lg-ask-user",
            "### `ask_user` → `END`\n"
            "- 에이전트: [[mod__agents__supervisor]]\n"
            "- 추가 정보나 객관식/주관식 폼(`idea_form`)이 필요할 때 사용자 응답 대기\n"
            "- 대시보드 오른쪽 질문 카드 렌더링",
            -830, -20, 420, 140, "4",
        ),
        text_node(
            "lg-idea",
            "### `prepare_idea_structuring` → `idea_phase`\n"
            "- 그래프: [[mod__graph__idea_graph]] | 로직: [[mod__agents__idea]] | 프롬프트: [[mod__prompts__idea_prompts]]\n"
            "- 4단계 추론: Analyze → Generate → Critique → Evaluate\n"
            "- 목차(`toc`) 및 섹션별 청사진(`blueprint`) 확정",
            -360, -20, 440, 150, "6",
        ),
        text_node(
            "lg-plan",
            "### `plan_phase` (`plan_subgraph`)\n"
            "- 그래프: [[mod__graph__plan_graph]] | 코어: [[mod__agents__plan_core__pipeline]], [[mod__agents__plan_core__generator]], [[mod__agents__plan_core__evaluator]]\n"
            "- 섹션별 초안 작성 및 품질 검증 (`schemas.py`: [[mod__agents__plan_core__schemas]])\n"
            "- 근거 부족 시 Research 요청 신호 발생",
            130, -20, 690, 150, "6",
        ),
        text_node(
            "lg-research",
            "### `research_phase` (`run_research_for_plan`)\n"
            "- 그래프: [[mod__graph__research_graph]] | 로직: [[mod__agents__research]] | 프롬프트: [[mod__prompts__research_prompts]]\n"
            "- `GlobalState` ↔ `ResearchState` 변환 래퍼\n"
            "- 쿼리 생성 → DuckDuckGo/Tavily 검색 → Qdrant 임베딩 저장 → 검증된 `evidence` 반환",
            -830, 180, 520, 160, "5",
        ),
        text_node(
            "lg-visual",
            "### `visual_subgraph`\n"
            "- 그래프: [[mod__graph__visual_graph]] | 코어: [[mod__agents__visual_core__router]], [[mod__agents__visual_core__generator]], [[mod__agents__visual_core__validator]]\n"
            "- 섹션 내용에 맞는 데이터 차트(Plotly) 및 Mermaid 다이어그램 생성",
            -270, 180, 520, 160, "5",
        ),
        text_node(
            "lg-edit",
            "### `edit_phase`\n"
            "- 그래프: [[mod__graph__edit_graph]] | 코어: [[mod__agents__edit_core__nodes]], [[mod__agents__edit_core__evaluation]]\n"
            "- 사용자 피드백 기반 특정 섹션/범위 수정 및 재평가",
            290, 180, 530, 160, "2",
        ),
        text_node(
            "lg-eval",
            "### 정량 평가 그래프 ([[mod__graph__evaluation_graph]] & [[mod__evaluate]])\n"
            "- 코어: [[mod__agents__evaluation]], [[mod__agents__evaluation_core__metrics]], [[mod__agents__evaluation_core__schemas]]\n"
            "- 생성된 기획서의 완성도·일관성·근거 충실도를 정량 지표로 채점 (문서: [[evaluation_agent]])",
            -830, 455, 1660, 125, "5",
        ),
    ]

    edges = [
        edge("lg-e-state-sup", "lg-state", "lg-supervisor", "GlobalState 전달", "bottom", "top", "3"),
        edge("lg-e-sup-ask", "lg-supervisor", "lg-ask-user", "ASK_USER", "bottom", "top", "4"),
        edge("lg-e-sup-idea", "lg-supervisor", "lg-idea", "RUN_IDEA_STRUCTURING", "bottom", "top", "6"),
        edge("lg-e-sup-plan", "lg-supervisor", "lg-plan", "RUN_PLANNING", "bottom", "top", "6"),
        edge("lg-e-sup-res", "lg-supervisor", "lg-research", "RUN_RESEARCH", "bottom", "top", "5"),
        edge("lg-e-sup-edit", "lg-supervisor", "lg-edit", "RUN_EDIT", "bottom", "top", "2"),
        edge("lg-e-plan-vis", "lg-plan", "lg-visual", "시각 자료 생성", "bottom", "top", "5"),
        edge("lg-e-idea-sup", "lg-idea", "lg-supervisor", "청사진 반영 후 복귀", "top", "bottom", "6"),
        edge("lg-e-res-sup", "lg-research", "lg-supervisor", "근거(evidence) 반영 후 복귀", "top", "bottom", "5"),
    ]
    return {"nodes": nodes, "edges": edges}


def build_storage_auth_canvas() -> dict:
    nodes = [
        group_node("st-grp-auth", "1. 계정 · 인증 · 세션 쿠키 (users & login_sessions)", -900, -420, 860, 360, "4"),
        group_node("st-grp-doc", "2. 문서 · 서식 초안 · 버전 이력 (documents & document_versions)", 0, -420, 900, 360, "2"),
        group_node("st-grp-job", "3. 에이전트 세션 · 멱등성 Job · 실행 이력 (sessions, jobs, agent_runs)", -900, -10, 1800, 340, "6"),

        text_node(
            "st-env-admin",
            "### `.env` 관리자 자동 동기화 ([[mod__storage__accounts]])\n"
            "- `ADMIN_EMAIL` + `ADMIN_PASSWORD` (4자 이상)\n"
            "- 서버 시작 시 `sync_admin_from_env()`가 [[db__users]] 테이블에 관리자 생성 또는 비밀번호 회전\n"
            "- 최초 생성 시 기존 `local` 소유 문서/Job을 관리자에게 자동 인계(`adopt_local`)",
            -870, -370, 800, 140, "4",
        ),
        text_node(
            "st-users-table",
            "### [[db__users]] & [[db__login_sessions]] 테이블\n"
            "- `users`: `id (PK)`, `key (UNIQUE)`, `email (UNIQUE)`, `password_hash (Argon2)`, `google_sub (UNIQUE)`, `is_admin`, `active`, `allow_google`\n"
            "- `login_sessions`: `token_hash (PK, SHA-256)`, `user_id (FK -> users.id)`, `csrf`, `expires_at` (12시간)\n"
            "- 인증 라우터: [[mod__web__auth]]",
            -870, -210, 800, 130, "4",
        ),
        text_node(
            "st-documents",
            "### [[db__documents]] 테이블 (현재 최신 문서 상태)\n"
            "- `id (PK)`, `owner_id (FK -> users.id)`, `title`\n"
            "- `draft` (Markdown), `draft_document` (Tiptap JSONB), `draft_revision` (낙관적 잠금 카운터)\n"
            "- `generated_markdown` (최신 AI 기획서 결과)\n"
            "- 저장소 모듈: [[mod__storage__repository]]",
            30, -370, 840, 145, "2",
        ),
        text_node(
            "st-versions",
            "### [[db__document_versions]] 테이블 (불변 버전 이력)\n"
            "- `id (PK)`, `document_id (FK -> documents.id)`, `kind` (`draft` | `generated`), `revision`\n"
            "- `markdown`, `document_json`, `source` (`create` | `save` | `copy` | `restore` | `ai`)\n"
            "- 이력 모듈: [[mod__storage__history]], [[mod__web__history_api]]",
            30, -205, 840, 125, "2",
        ),
        text_node(
            "st-sessions",
            "### [[db__sessions]] 테이블 (LangGraph 상태 스냅샷)\n"
            "- `id (PK)`, `document_id (UNIQUE FK -> documents.id)`\n"
            "- `status` (`ready` | `running` | `error`), `stage`, `error`, `run_token`\n"
            "- `state (JSONB)`: 직렬화된 `GlobalState` (`messages`, `idea`, `plan`, `supervision`)",
            -870, 45, 560, 250, "6",
        ),
        text_node(
            "st-jobs",
            "### [[db__jobs]] 테이블 (요청 멱등성 & 비동기 작업 추적)\n"
            "- `id (PK)`, `owner_id (FK -> users.id)`, `session_id (FK -> sessions.id)`\n"
            "- `request_key` (`Idempotency-Key`), `input_hash (SHA-256)`, `kind` (`planning` | `revision`)\n"
            "- `UNIQUE(owner_id, request_key)`: 동일 키+동일 입력은 기존 Job 반환, 다른 입력은 `409 Conflict`\n"
            "- `base_revision` 기록: AI 실행 중 사용자가 초안을 편집해도 서로 덮어쓰지 않음",
            -280, 45, 620, 250, "6",
        ),
        text_node(
            "st-agent-runs",
            "### [[db__agent_runs]] 테이블 (실행 감사 로그)\n"
            "- `id (PK)`, `session_id (FK -> sessions.id)`, `stage`\n"
            "- `status` (`running` | `completed` | `error` | `interrupted`)\n"
            "- 서버 강제 종료 후 재시작 시 `store.initialize()`가 미완료 작업을 `interrupted`로 일괄 정리",
            370, 45, 500, 250, "6",
        ),
    ]

    edges = [
        edge("st-e-admin-users", "st-env-admin", "st-users-table", "생성 / 비밀번호 회전", "bottom", "top", "4"),
        edge("st-e-users-doc", "st-users-table", "st-documents", "owner_id (1:N)", "right", "left", "4"),
        edge("st-e-doc-ver", "st-documents", "st-versions", "document_id (1:N)", "bottom", "top", "2"),
        edge("st-e-doc-sess", "st-documents", "st-sessions", "document_id (1:1)", "bottom", "top", "2"),
        edge("st-e-sess-jobs", "st-sessions", "st-jobs", "session_id (1:N)", "right", "left", "6"),
        edge("st-e-jobs-runs", "st-jobs", "st-agent-runs", "실행 기록", "right", "left", "6"),
    ]
    return {"nodes": nodes, "edges": edges}


NOTES: dict[str, str] = {
    "00-Index.md": """---
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
""",
    "01-Web-and-Editor.md": """---
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
""",
    "02-Storage-and-Auth.md": """---
title: 02. PostgreSQL 영속화 · 인증 · Job 계층
tags:
  - architecture
  - layer/postgres
---

# 02. PostgreSQL 영속화 · 인증 · Job 계층 (`src/storage/`)

상위 허브: [[00-Index]] | 세부 캔버스: [[storage-auth-flow.canvas]]
연관 문서: [[postgresql-local]], [[postgresql-accounts-jobs]], [[postgresql-storage-design]], [[01-Web-and-Editor]]

## PostgreSQL 7개 테이블 노드 (Graph View 연동)

- [[db__users]] (`users`) — 계정, Argon2 해시, Google `sub`, 관리자 권한
- [[db__login_sessions]] (`login_sessions`) — 세션 쿠키 SHA-256 해시, CSRF 토큰, 만료 시각
- [[db__documents]] (`documents`) — 초안 Markdown, Tiptap JSONB, `draft_revision` 낙관적 잠금, 최신 AI 기획서
- [[db__document_versions]] (`document_versions`) — 모든 저장·생성·복원 스냅샷 이력
- [[db__sessions]] (`sessions`) — LangGraph `GlobalState` JSONB 스냅샷 및 진행 단계
- [[db__jobs]] (`jobs`) — `Idempotency-Key` 기반 중복 방지 및 비동기 작업 결과
- [[db__agent_runs]] (`agent_runs`) — 에이전트 실행 단계별 감사 로그

## 저장소 & 마이그레이션 코드 모듈 노드

- [[mod__storage__database]] (`src/storage/database.py`)
- [[mod__storage__repository]] (`src/storage/repository.py`)
- [[mod__storage__history]] (`src/storage/history.py`)
- [[mod__storage__accounts]] (`src/storage/accounts.py`)
- [[mod__storage__import_drafts]] (`src/storage/import_drafts.py`)
- [[mod__migrations__env]] (`migrations/env.py`)
- [[mod__migrations__versions__001_storage]] (`migrations/versions/001_storage.py`)
- [[mod__migrations__versions__002_history_auth]] (`migrations/versions/002_history_auth.py`)

## PostgreSQL 데이터베이스 ERD

```mermaid
erDiagram
    users ||--o{ login_sessions : "has"
    users ||--o{ documents : "owns"
    users ||--o{ jobs : "requests"
    documents ||--o{ document_versions : "versions"
    documents ||--|| sessions : "binds"
    sessions ||--o{ jobs : "runs"
    sessions ||--o{ agent_runs : "logs"

    users {
        text id PK
        text key UK
        text email UK
        text password_hash
        text google_sub UK
        boolean is_admin
        boolean active
        boolean allow_google
        timestamptz created_at
    }
    login_sessions {
        text token_hash PK
        text user_id FK
        text csrf
        timestamptz expires_at
        timestamptz created_at
    }
    documents {
        text id PK
        text owner_id FK
        text title
        text draft
        jsonb draft_document
        integer draft_revision
        text generated_markdown
        timestamptz created_at
        timestamptz updated_at
    }
    document_versions {
        bigserial id PK
        text document_id FK
        text kind
        integer revision
        text markdown
        jsonb document_json
        text source
        timestamptz created_at
    }
    sessions {
        text id PK
        text document_id FK
        text status
        text stage
        text error
        text run_token
        jsonb state
        timestamptz created_at
        timestamptz updated_at
    }
    jobs {
        text id PK
        text owner_id FK
        text session_id FK
        text request_key
        text input_hash
        jsonb input
        text kind
        text status
        integer base_revision
        jsonb result
        text error
        timestamptz created_at
        timestamptz finished_at
    }
    agent_runs {
        text id PK
        text session_id FK
        text stage
        text status
        text error
        timestamptz started_at
        timestamptz finished_at
    }
```
""",
    "03-LangGraph-Agents.md": """---
title: 03. LangGraph 멀티 에이전트 파이프라인
tags:
  - architecture
  - layer/langgraph
---

# 03. LangGraph 멀티 에이전트 파이프라인 (`src/graph/` & `src/agents/`)

상위 허브: [[00-Index]] | 세부 캔버스: [[langgraph-flow.canvas]]
연관 노트: [[01-Web-and-Editor]], [[04-Models-and-Config]], [[evaluation_agent]]

## 에이전트별 그래프 · 로직 · 상태 · 프롬프트 모듈 노드

| 에이전트 | 그래프 (`src/graph/`) | 에이전트 로직 (`src/agents/`) | 상태 (`src/state/`) | 프롬프트 (`src/prompts/`) |
|---|---|---|---|---|
| **Supervisor** | [[mod__graph__supervisor_graph]] | [[mod__agents__supervisor]] | [[mod__state__base]] | [[mod__prompts__supervisor_prompt]] |
| **Idea** | [[mod__graph__idea_graph]] | [[mod__agents__idea]] | [[mod__state__idea]] | [[mod__prompts__idea_prompts]] |
| **Plan** | [[mod__graph__plan_graph]] | [[mod__agents__plan]], [[mod__agents__plan_core__pipeline]], [[mod__agents__plan_core__nodes]], [[mod__agents__plan_core__generator]], [[mod__agents__plan_core__evaluator]], [[mod__agents__plan_core__schemas]], [[mod__agents__plan_core__logger]] | [[mod__state__plan]] | [[mod__prompts__plan_prompts]] |
| **Research** | [[mod__graph__research_graph]] | [[mod__agents__research]] | [[mod__state__research]] | [[mod__prompts__research_prompts]] |
| **Visual** | [[mod__graph__visual_graph]] | [[mod__agents__visual]], [[mod__agents__visual_core__router]], [[mod__agents__visual_core__nodes]], [[mod__agents__visual_core__generator]], [[mod__agents__visual_core__validator]], [[mod__agents__visual_core__schemas]] | [[mod__state__visual]] | [[mod__prompts__visual_prompts]] |
| **Edit** | [[mod__graph__edit_graph]] | [[mod__agents__edit]], [[mod__agents__edit_core__nodes]], [[mod__agents__edit_core__evaluation]] | [[mod__state__edit]] | [[mod__prompts__edit_prompts]] |
| **Evaluation** | [[mod__graph__evaluation_graph]] | [[mod__evaluate]], [[mod__agents__evaluation]], [[mod__agents__evaluation_core__metrics]], [[mod__agents__evaluation_core__schemas]] | [[mod__agents__evaluation_core__schemas]] | [[mod__prompts__evaluation_prompts]] |

## Supervisor 상태 전이 다이어그램

```mermaid
stateDiagram-v2
    [*] --> supervisor
    supervisor --> ask_user : ASK_USER
    supervisor --> prepare_idea_structuring : RUN_IDEA_STRUCTURING
    supervisor --> plan_phase : RUN_PLANNING
    supervisor --> research_phase : RUN_RESEARCH
    supervisor --> edit_phase : RUN_EDIT
    supervisor --> [*] : Refresh (다음 라운드 재실행)

    prepare_idea_structuring --> idea_phase
    idea_phase --> supervisor
    plan_phase --> supervisor
    research_phase --> supervisor
    edit_phase --> supervisor
    ask_user --> [*]
```
""",
    "04-Models-and-Config.md": """---
title: 04. 공통 모델 팩토리 · 설정 계층
tags:
  - architecture
  - layer/model
---

# 04. 공통 모델 팩토리 · 설정 계층 (`src/models/` & `src/config/`)

상위 허브: [[00-Index]] | 연관 노트: [[03-LangGraph-Agents]], [[ollama-docker]], [[dashboard]]

## 코드 모듈 노드

- [[mod__config__config]] (`src/config/config.py`) — 환경변수 및 모델 프리셋(`OLLAMA_MODEL_PRESETS`, `HF_MODEL_PRESETS`, `GEMINI_MODEL_PRESETS`)
- [[mod__models__llm]] (`src/models/llm.py`) — `get_llm()`, `get_mini_llm()` 공통 모델 팩토리
- [[mod__models__embeddings]] (`src/models/embeddings.py`) — FastEmbed CPU 임베딩 팩토리

## 지원 LLM 제공자 및 프리셋 (`src/models/llm.py`)

```mermaid
flowchart LR
    CALL["에이전트 호출\nget_llm() / get_mini_llm()"] --> FACTORY["src/models/llm.py"]
    FACTORY -->|LLM_PROVIDER=ollama| OLLAMA["ChatOllama\n- qwen3.5:4b (기본)\n- qwen3.8:27b (Qwen/Qwen3.8-27B)"]
    FACTORY -->|LLM_PROVIDER=gemini| GEMINI["ChatGoogleGenerativeAI\n- gemini-2.5-flash\n- gemini-2.5-pro\n- gemini-2.5-flash-lite"]
    FACTORY -->|LLM_PROVIDER=openai| OPENAI["ChatOpenAI\n- Qwen/Qwen3.8-27B (vLLM/SGLang)\n- OpenAI GPT 시리즈"]
    FACTORY -->|LLM_PROVIDER=upstage| UPSTAGE["ChatUpstage\n- Solar 시리즈"]
```
""",
}


def write_obsidian_config() -> None:
    OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)
    app_config = {
        "userIgnoreFilters": [
            ".venv/",
            "node_modules/",
            ".git/",
            "__pycache__/",
            ".pytest_cache/",
            ".cache/",
            ".runtime/",
            "qdrant_data/",
            "output/",
            "logs/",
            "src/web/static/editor.bundle.js",
        ],
        "useMarkdownLinks": False,
        "newLinkFormat": "shortest",
        "showUnsupportedFiles": False,
    }
    graph_config = {
        "collapse-filter": False,
        "search": "",
        "showTags": False,
        "showAttachments": False,
        "hideUnresolved": False,
        "showOrphans": True,
        "collapse-color-groups": False,
        "colorGroups": [
            {"query": "tag:#moc", "color": {"a": 1, "rgb": 16761095}},
            {"query": "tag:#layer/langgraph", "color": {"a": 1, "rgb": 10181046}},
            {"query": "tag:#layer/agent", "color": {"a": 1, "rgb": 11437567}},
            {"query": "tag:#layer/state", "color": {"a": 1, "rgb": 16098851}},
            {"query": "tag:#layer/prompt", "color": {"a": 1, "rgb": 13408767}},
            {"query": "tag:#layer/postgres", "color": {"a": 1, "rgb": 15631670}},
            {"query": "tag:#layer/web", "color": {"a": 1, "rgb": 3581519}},
            {"query": "tag:#layer/model", "color": {"a": 1, "rgb": 3787917}},
        ],
        "collapse-display": False,
        "showArrow": True,
        "textFadeMultiplier": -1,
        "nodeSizeMultiplier": 1.15,
        "lineSizeMultiplier": 1,
    }
    (OBSIDIAN_DIR / "app.json").write_text(
        json.dumps(app_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OBSIDIAN_DIR / "graph.json").write_text(
        json.dumps(graph_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def sync_windows_vault(target: Path) -> None:
    """Mirror docs/ (including generated code/table notes), src/, migrations/, scripts/, and .obsidian/ to C:\\."""
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(OBSIDIAN_DIR, target / ".obsidian", dirs_exist_ok=True)
    shutil.copytree(ROOT / "docs", target / "docs", dirs_exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".env", "editor.bundle.js")
    for folder in ("src", "migrations", "scripts"):
        src_dir = ROOT / folder
        if src_dir.is_dir():
            shutil.copytree(src_dir, target / folder, dirs_exist_ok=True, ignore=ignore)
    for extra in ("README.md", "AGENTS.md", "compose.yaml", ".env.example"):
        src = ROOT / extra
        if src.is_file():
            shutil.copy2(src, target / extra)
    print(f"[win-vault] synced full project graph to {target} (Windows: C:\\Users\\141\\div-obsidian-vault)")


def main() -> None:
    ARCH_DIR.mkdir(parents=True, exist_ok=True)
    modules = collect_python_modules()
    generate_module_notes(modules)
    generate_table_notes()
    print(f"[ast]    generated {len(modules)} Python module notes in docs/architecture/modules/")
    print(f"[db]     generated {len(POSTGRES_TABLES)} PostgreSQL table notes in docs/architecture/tables/")

    canvases = {
        "div-architecture.canvas": build_div_architecture_canvas(),
        "langgraph-flow.canvas": build_langgraph_flow_canvas(),
        "storage-auth-flow.canvas": build_storage_auth_canvas(),
    }
    for filename, payload in canvases.items():
        validate_canvas(filename, payload)
        path = ARCH_DIR / filename
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[canvas] {path.relative_to(ROOT)} ({len(payload['nodes'])} nodes, {len(payload['edges'])} edges)")

    for filename, content in NOTES.items():
        path = ARCH_DIR / filename
        path.write_text(content.lstrip(), encoding="utf-8")
        print(f"[note]   {path.relative_to(ROOT)}")

    write_obsidian_config()
    if WINDOWS_VAULT_DEFAULT.parent.is_dir():
        sync_windows_vault(WINDOWS_VAULT_DEFAULT)


if __name__ == "__main__":
    main()
