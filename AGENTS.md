# Repository Guidelines

## Project Structure & Module Organization

`src/agents/` contains LangGraph agent logic and agent-specific pipelines. `src/graph/` assembles the graphs; `src/state/`, `src/prompts/`, `src/models/`, and `src/config/` hold shared state, prompts, model factories, and settings. The FastAPI dashboard lives in `src/web/`: Python API, static HTML/CSS/JavaScript, and the Tiptap editor source in `src/web/editor/`. Its checked-in browser bundle is `src/web/static/editor.bundle.js`. Evaluation code and reports are in `src/agents/evaluation*`, `src/graph/evaluation_graph.py`, and `src/evaluate.py`. Tests live in `tests/`; generated documents and local runtime data belong in ignored `output/`, `logs/`, and `qdrant_data/` directories.

## Build, Test, and Development Commands

- `uv sync` installs Python dependencies; `uv run pytest -q` runs the Python suite.
- `uv run uvicorn web.app:app --app-dir src --host 127.0.0.1 --port 8000` starts the dashboard at `http://127.0.0.1:8000`.
- `uv run streamlit run src/main.py` runs the legacy Streamlit interface.
- After changing `src/web/editor/editor.js`, run `npm ci` and `npm run build:editor` to refresh the local bundle. No Node.js process is needed at runtime.
- `uv run python tests/dashboard_browser_smoke.py` exercises the dashboard in installed Microsoft Edge; start the API first.

## Coding Style & Naming Conventions

Use four spaces in Python, snake_case for modules, functions, and variables, and PascalCase for Pydantic models and state types. Keep shared model calls behind `src/models/llm.py`, configuration in `src/config/config.py` or `.env`, and UI assets under `src/web/`. Use descriptive JavaScript functions and kebab-case DOM IDs. Preserve Korean user-facing copy and keep API keys out of source control.

## Testing Guidelines

Use pytest. Name test modules `test_*.py` and cases `test_<behavior>`. Cover graph routing and state transitions with mocked model calls so routine tests do not require Ollama or paid APIs. For editor or layout changes, run the browser smoke test and check a narrow viewport as well as desktop. Update tests when changing request schemas, Markdown serialization, or model configuration.

## Commit & Pull Request Guidelines

Recent history uses short imperative subjects, often with prefixes such as `feat(Plan):`, `fix(Prompts):`, and `docs:`. Keep commits focused and use `feat(area):`, `fix(area):`, or `docs:` where suitable. Pull requests should explain the user-visible change, note configuration or model requirements, include relevant test results, and add a dashboard screenshot when the layout changes. Never commit `.env`, API keys, model files, vector data, or generated documents.

## Security & Configuration

Copy `.env.example` to `.env` for local secrets and remove secrets before sharing logs. The default Ollama provider runs a local model; set the provider and model deliberately when switching providers. Validate API input and sanitize rendered Markdown. Keep static editor dependencies bundled locally rather than requiring a third-party CDN at runtime.
