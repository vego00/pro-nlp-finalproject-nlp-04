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


## External Download and Installation Policy

### Principle
The user is responsible for downloading external artifacts
and installing dependencies. Codex handles code, configuration,
analysis, and verification.

### Prohibited Actions
- Do not directly download model weights, datasets, binaries,
  archives, Docker images, or external dependencies.
- Do not execute download or installation commands such as:
  `ollama pull`, `hf download`, `wget`, `curl -O`,
  `git clone`, `docker pull`, `pip install`,
  `uv sync`, `npm install`, or `apt install`.
- Do not execute scripts that indirectly download artifacts.
- Do not run automatic download retries or wait for downloads.
- Do not initiate downloads even when they are necessary
  to complete the requested task.

### Required Behavior
When a download or installation is needed:

1. Inspect local configuration and determine what is required.
2. Explain why the artifact is needed.
3. Provide exact, copy-paste-ready commands for the user.
4. State expected size, download location, and prerequisites
   when known.
5. Provide commands for verifying successful installation.
6. Let the user execute the commands manually.
7. Continue with local-only tasks that do not need the artifact.
8. Mark download-dependent checks as NOT VERIFIED until
   the artifact is available.

### Allowed Actions
- Editing and generating project code.
- Modifying configuration and documentation.
- Inspecting existing local files and installed tools.
- Running tests that use only existing local dependencies.
- Querying already-running local services and APIs.

### Reporting
Separate results into:
- Completed
- Requires User Execution
- Not Verified

Never claim that a model, dependency, or artifact was
installed unless its presence was actually verified.
