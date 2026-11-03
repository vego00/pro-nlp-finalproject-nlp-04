---
title: "src/config/config.py"
tags:
  - code
  - layer/model
---

# `src/config/config.py`

- **소속 계층 태그**: `#layer/model`
- **상위 아키텍처 노트**: [[00-Index]], [[04-Models-and-Config]]
- **내부 모듈 의존성(Imports)**: 없음

> Edit defaults here or override them in the root .env; restart to apply.

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- 없음

## 소스 코드 미리보기 (`src/config/config.py`)

```python
"""Edit defaults here or override them in the root .env; restart to apply."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

# 모델 선택: 아래 두 값을 수정하고 서버를 재시작하세요.
# .env에 LLM_PROVIDER / LLM_MODEL이 있으면 .env 값이 우선합니다.
# ollama는 로컬 무료 실행, openai / gemini / upstage는 API 키가 필요합니다.
DEFAULT_LLM_PROVIDER = "ollama"
DEFAULT_LLM_MODEL = "qwen3.5:4b"
# Recommended model presets (any model identifier is still accepted in LLM_MODEL).
OLLAMA_MODEL_PRESETS = (
    "qwen3.5:4b",
    "qwen3.8:27b",  # Hugging Face: Qwen/Qwen3.8-27B (24GB+ VRAM / Colab GPU 권장)
)
HF_MODEL_PRESETS = (
    "Qwen/Qwen3.8-27B",  # https://huggingface.co/Qwen/Qwen3.8-27B (vLLM / SGLang 등 OpenAI 호환 서버용)
)
GEMINI_MODEL_PRESETS = (
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-lite",
)
MODEL_PRESETS = {
    "ollama": OLLAMA_MODEL_PRESETS,
    "openai": HF_MODEL_PRESETS,
    "gemini": GEMINI_MODEL_PRESETS,
}
PROVIDER_ALIASES = {"google": "gemini"}
RAW_LLM_PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER).strip().lower()
LLM_PROVIDER = PROVIDER_ALIASES.get(RAW_LLM_PROVIDER, RAW_LLM_PROVIDER)
LLM_MODEL = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL).strip()
LLM_MINI_MODEL = os.getenv("LLM_MINI_MODEL", LLM_MODEL)
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "300"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_THINKING = os.getenv("OLLAMA_THINKING", "false").lower() == "true"
API_KEY = os.getenv("API_KEY")  # Legacy Upstage alias
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY") or API_KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT") or None
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# CPU embeddings leave GPU memory available for the chat model.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
MODEL_CACHE_DIR = ROOT_DIR / ".cache" / "models"
QDRANT_PATH = ROOT_DIR / "qdrant_data"
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo").lower()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SEARCH_MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS", "3"))
SEARCH_MAX_QUERIES = int(os.getenv("SEARCH_MAX_QUERIES", "3"))
DATA_DIR = ROOT_DIR / "data"
GRAPH_RECURSION_LIMIT = 80
GRAPH_MAX_ROUNDS = 30

DATABASE_URL = os.getenv("DATABASE_URL", "")

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
AUTH_SECRET = os.getenv("AUTH_SECRET", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
AUTH_COOKIE_SECURE = APP_BASE_URL.startswith("https://")
# Initial administrator, synchronised to the database on every server start.
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
```
