---
title: "src/models/llm.py"
tags:
  - code
  - layer/model
---

# `src/models/llm.py`

- **소속 계층 태그**: `#layer/model`
- **상위 아키텍처 노트**: [[00-Index]], [[04-Models-and-Config]]
- **내부 모듈 의존성(Imports)**: [[mod__config__config]]

> One model factory for every agent; no network calls at import time.

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def get_llm(model, temperature, max_tokens, reasoning_effort)`
- `def get_mini_llm(temperature, max_tokens)`

## 소스 코드 미리보기 (`src/models/llm.py`)

```python
"""One model factory for every agent; no network calls at import time."""
from config import config as settings


def get_llm(model=None, temperature=0.7, max_tokens=None, reasoning_effort=None,
            *, json_mode=False):
    model = model or settings.LLM_MODEL
    if not model:
        raise ValueError("src/config/config.py 또는 .env에 LLM_MODEL을 지정하세요.")
    tokens = min(max_tokens or settings.LLM_MAX_TOKENS, settings.LLM_MAX_TOKENS)
    provider = settings.PROVIDER_ALIASES.get(settings.LLM_PROVIDER, settings.LLM_PROVIDER)
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        options = dict(model=model, base_url=settings.OLLAMA_BASE_URL,
                       temperature=temperature, num_predict=tokens,
                       num_ctx=settings.OLLAMA_NUM_CTX, reasoning=settings.OLLAMA_THINKING,
                       client_kwargs={"timeout": settings.LLM_TIMEOUT})
        if json_mode:
            options["format"] = "json"
        return ChatOllama(**options)
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini 사용 시 .env에 GEMINI_API_KEY 또는 GOOGLE_API_KEY가 필요합니다.")
        options = dict(model=model, google_api_key=settings.GEMINI_API_KEY,
                       temperature=temperature, max_output_tokens=tokens,
                       timeout=settings.LLM_TIMEOUT, max_retries=1)
        if json_mode:
            options["response_mime_type"] = "application/json"
        return ChatGoogleGenerativeAI(**options)
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI 사용 시 .env에 OPENAI_API_KEY가 필요합니다.")
        options = dict(model=model, api_key=settings.OPENAI_API_KEY,
                       base_url=settings.OPENAI_BASE_URL, max_tokens=tokens,
                       timeout=settings.LLM_TIMEOUT, max_retries=1)
        if settings.OPENAI_REASONING_EFFORT:
            options["reasoning_effort"] = settings.OPENAI_REASONING_EFFORT
        else:
            options["temperature"] = temperature
        llm = ChatOpenAI(**options)
    elif provider == "upstage":
        from langchain_upstage import ChatUpstage
        if not settings.UPSTAGE_API_KEY:
            raise ValueError("Upstage 사용 시 .env에 UPSTAGE_API_KEY가 필요합니다.")
        options = dict(model=model, api_key=settings.UPSTAGE_API_KEY,
                       temperature=temperature, max_tokens=tokens,
                       timeout=settings.LLM_TIMEOUT, max_retries=1)
        if reasoning_effort:
            options["reasoning_effort"] = reasoning_effort
        llm = ChatUpstage(**options)
    else:
        raise ValueError(f"지원하지 않는 LLM_PROVIDER: {provider}")
    return llm.bind(response_format={"type": "json_object"}) if json_mode else llm


def get_mini_llm(temperature=0.7, max_tokens=None, *, json_mode=False):
    return get_llm(model=settings.LLM_MINI_MODEL, temperature=temperature,
                   max_tokens=max_tokens, json_mode=json_mode)
```
