---
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
    CALL["에이전트 호출
get_llm() / get_mini_llm()"] --> FACTORY["src/models/llm.py"]
    FACTORY -->|LLM_PROVIDER=ollama| OLLAMA["ChatOllama
- qwen3.5:4b (기본)
- qwen3.8:27b (Qwen/Qwen3.8-27B)"]
    FACTORY -->|LLM_PROVIDER=gemini| GEMINI["ChatGoogleGenerativeAI
- gemini-2.5-flash
- gemini-2.5-pro
- gemini-2.5-flash-lite"]
    FACTORY -->|LLM_PROVIDER=openai| OPENAI["ChatOpenAI
- Qwen/Qwen3.8-27B (vLLM/SGLang)
- OpenAI GPT 시리즈"]
    FACTORY -->|LLM_PROVIDER=upstage| UPSTAGE["ChatUpstage
- Solar 시리즈"]
```
