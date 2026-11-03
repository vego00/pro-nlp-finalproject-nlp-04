# DIV(Design In Vibe): AI-Powered Agentic Writing Assistant

## FastAPI + HTML 대시보드 (기본 실행)

```powershell
uv sync
docker compose up -d --wait
docker compose exec ollama ollama pull qwen3.5:4b
uv run alembic upgrade head
uv run uvicorn web.app:app --app-dir src --host 127.0.0.1 --port 8000
```

http://127.0.0.1:8000 에서 사용합니다. `src/config/config.py`의 `DEFAULT_LLM_PROVIDER`, `DEFAULT_LLM_MODEL`을 수정하고 서버를 재시작하면 모델을 변경할 수 있습니다. `.env`에 지정한 모델 설정이 있으면 우선 적용됩니다.

기본값은 무료 로컬 Ollama 모델입니다. 모델 설치와 환경변수, 대시보드 기능은 [대시보드 실행 안내](docs/dashboard.md)를 참고하세요. 아래 Streamlit 실행 방법은 기존 UI용입니다.

**DIV(Design In Vibe)** is an advanced AI agent system designed to transform abstract user ideas into concrete, comprehensive project plans and documents. Built with **LangGraph** and **Streamlit**, it orchestrates a team of specialized agents—Idea, Plan, Research, and Visual—under a central Supervisor to collaboratively author high-quality content.

---

로컬 PostgreSQL 실행 환경은 [Docker Desktop + PostgreSQL 안내](docs/postgresql-local.md)를 참고하세요. 앱 실행 전에 `uv run alembic upgrade head`로 DB 스키마를 준비하세요.

## 🚀 Key Features

- **Multi-Agent Orchestration**: A Supervisor agent intelligently routes tasks to specialized sub-agents based on user intent.
- **Idea Structuring**: Transforms vague inputs into structured blueprints with clear objectives and scope.
- **Deep Research**: Autonomous research agent performs web searches (Tavily/DuckDuckGo) to gather evidence and validate claims.
- **Visual Generation**: Automatically generates data visualizations (Charts, Mermaid diagrams) to support the content.
- **Incremental Writing**: Generates long-form documents section by section, ensuring coherence and depth.
- **Interactive UI**: User-friendly Streamlit interface for real-time interaction and feedback.

---

## 🏗️ System Architecture

### 1. Supervisor Graph (Central Control)
The **Supervisor** serves as the central control unit, analyzing user input and routing tasks to the appropriate sub-agents.

```mermaid
graph TD
    start((Start)) --> supervisor
    
    supervisor[Supervisor Node]
    router{Router Logic}
    
    supervisor --> router
    
    router -->|ASK_USER| ask_user[Ask User]
    router -->|RUN_IDEA_STRUCTURING| prepare_idea[Prepare Idea Structuring]
    router -->|RUN_PLANNING| plan_phase[Plan Phase]
    router -->|RUN_RESEARCH| research_phase[Research Phase]
    
    ask_user --> user_input((End/User Input))
    
    prepare_idea --> idea_graph[[Idea Subgraph]]
    idea_graph --> supervisor
    
    plan_phase[[Plan Subgraph]] --> supervisor
    
    research_phase[[Research Subgraph]] --> supervisor
    
    style supervisor fill:#f9f,stroke:#333,stroke-width:4px
    style router fill:#fff,stroke:#333,stroke-dasharray: 5 5
```

### 3. Interaction Sequence Diagram
This sequence diagram illustrates the detailed interaction flow between the Supervisor and the Agents.

```mermaid
sequenceDiagram
    participant Idea as Idea Agent
    participant Supervisor as Supervisor
    participant Plan as Plan Agent
    participant Research as Research Agent

    Note over Supervisor: Analyze User Input
    
    Supervisor->>Idea: Request Idea Refinement
    Note over Idea: Analyze & Structure Idea
    
    loop Idea Evolution
        Idea->>Idea: 4-Step Reasoning (Analyze-Generate-Critique-Evaluate)
    end
    
    Idea-->>Supervisor: Return Structured Idea
    
    Supervisor->>Plan: Request Plan Drafting
    
    Note over Plan: Attempt Draft Section
    Note over Plan: Evaluate Research Need
    
    alt Information Gap (Needs Research)
        Plan-->>Supervisor: Signal Research Need
        Note over Supervisor: Detect Research Mode
        
        Supervisor->>Research: Execute Research Task
        
        Note over Research: Query Gen -> Web Search -> Analysis
        loop Deep Search
            Research->>Research: Collect & Verify Info
        end
        
        Research-->>Supervisor: Return Verified Evidence
        Supervisor->>Plan: Rewrite Section (Resume Planning)
    end
```

---

## 🛠️ Installation

This project is managed with **[uv](https://github.com/astral-sh/uv)**, a fast Python package installer and resolver.

### 1. Clone the repository
```bash
git clone https://github.com/boostcampaitech8/pro-nlp-finalproject-nlp-04.git
cd pro-nlp-finalproject-nlp-04
```

### 2. Install dependencies
Ensure you have `uv` installed. If not, install it first:
```bash
pip install uv
```

Then, sync the project dependencies:
```bash
uv sync
```

---

## ⚙️ Configuration

Create a `.env` file in the root directory and add your API keys. Refer to `src/config/config.py` for variables.

```ini
# .env
UPSTAGE_API_KEY=your_solar_pro_api_key
TAVILY_API_KEY=your_tavily_api_key
```

---

## ▶️ Usage

기획서 정량 평가 에이전트의 실행 방법과 지표 정의는 [평가 에이전트 문서](docs/evaluation_agent.md)를 참고하세요.

Run the Streamlit application using `uv`:

```bash
uv run streamlit run src/main.py
```

The application will open in your default browser. You can start by entering a topic or idea in the chat input.

---

## 📂 Project Structure

```
.
├── src/
│   ├── agents/           # Agent implementations (Supervisor, Idea, Plan, Research, Visual)
│   ├── config/           # Configuration and environment variables
│   ├── front/            # Streamlit UI components
│   ├── graph/            # LangGraph state definitions
│   ├── models/           # LLM model wrappers
│   ├── prompts/          # System prompts for agents
│   └── state/            # State schema definitions
├── exp/                  # Experiments and test scripts
├── output/               # Generated documents and artifacts
├── pyproject.toml        # Project dependencies and settings
└── README.md             # Project documentation
```

---

## 🤝 Contribution

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feat/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feat/AmazingFeature`)
5. Open a Pull Request
