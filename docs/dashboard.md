# FastAPI + HTML 대시보드

## 실행

```powershell
uv sync
uv run uvicorn web.app:app --app-dir src --host 127.0.0.1 --port 8000
```

브라우저에서 http://127.0.0.1:8000 을 엽니다. 기존 Streamlit 화면은 `uv run streamlit run src/main.py`로 별도 실행할 수 있습니다.

## 모델 선택

`src/config/config.py` 맨 위의 두 값을 수정하고 서버를 재시작하세요.

```python
DEFAULT_LLM_PROVIDER = "ollama"
DEFAULT_LLM_MODEL = "qwen3.5:4b"
```

모든 에이전트는 공통 모델 팩토리를 사용합니다. 빠른 보조 모델을 따로 쓰려면 `.env`에 `LLM_MINI_MODEL`을 지정하세요. 기본값은 본 모델과 같습니다.

`.env` 또는 프로세스 환경변수에 `LLM_PROVIDER`, `LLM_MODEL`, `LLM_MINI_MODEL`이 있으면 파일 기본값보다 우선합니다. 파일만으로 선택하려면 해당 환경변수를 제거하세요. API 키는 `.env`에만 보관하세요.

무료 로컬 실행은 [Ollama](https://ollama.com/) 설치 후 선택한 모델을 내려받아 사용합니다.

```powershell
ollama pull qwen3.5:4b
ollama serve
```

Ollama 앱이 이미 실행 중이면 `ollama serve`는 필요 없습니다. 다른 모델을 선택했다면 `pull`에도 같은 모델명을 사용하세요. 모델 다운로드와 실행에는 디스크 공간과 메모리가 필요합니다. 대시보드의 연결 확인은 [Ollama 모델 목록 API](https://docs.ollama.com/api/tags)로 본 모델과 보조 모델 설치 여부를 확인합니다.

`openai`, `upstage`도 선택할 수 있으며 해당 제공자의 모델명과 `OPENAI_API_KEY` 또는 `UPSTAGE_API_KEY`를 함께 설정해야 합니다. 이 API들은 무료 로컬 실행과 별개입니다. 검색 기본값은 `duckduckgo`이며 Tavily를 쓰려면 `SEARCH_PROVIDER=tavily`, `TAVILY_API_KEY`를 지정합니다.

## 사용 흐름

중앙 **문서 편집**은 [Tiptap](https://tiptap.dev/docs/editor/extensions/functionality/starterkit) 기반 서식 편집기입니다. 제목 1~3, 굵게·기울임·취소선, 링크, 글머리·번호 목록, 체크리스트, 인용, 코드 블록, 구분선, 표를 지원합니다. 빈 줄에 `/`를 입력하면 블록 메뉴가 열리고 방향키·Enter로 선택할 수 있습니다. 표 셀을 클릭하면 행·열 추가 및 삭제 메뉴가 나타납니다. 왼쪽 목차는 문서 제목과 연동됩니다. Ctrl+Z / Ctrl+Shift+Z로 실행 취소·다시 실행이 가능합니다.

입력 중에는 브라우저에 임시 저장하고 1.2초 동안 입력이 멈추면 서버에 자동 저장합니다. **저장**(Ctrl/Cmd+S), **읽기 모드**, **초안 다운로드**도 사용할 수 있습니다. `output/drafts/<세션 ID>.json`에는 서식·체크 상태를 포함한 문서 구조, `.md`에는 Markdown이 저장됩니다. 같은 브라우저에서 새로고침 및 서버 재시작 후 문서를 복구합니다. 기존 Markdown 초안도 편집기로 가져옵니다. 새 문서를 열면 이전 문서의 실행 취소 기록은 초기화됩니다.

문장을 선택하고 **AI에게 요청**을 누르면 오른쪽에 선택 영역 편집기가 열립니다. 다듬기·줄이기·구체화 또는 직접 입력한 지시로 수정안을 생성하고 **선택 영역에 반영**을 눌러 적용합니다. 그동안 문서가 수정되면 이전 수정안 적용을 차단합니다. 원문 변경은 Ctrl+Z로 되돌릴 수 있습니다. 모델 연결 실패 시 원문은 유지됩니다.

오른쪽 일반 채팅의 **작성한 문서를 AI에게 함께 전달** 옵션은 기존 에이전트의 기획 흐름에 최신 문서를 전달합니다. **AI 작성 결과**는 별도 탭에서 확인하고 **문서 끝에 추가**할 수 있습니다. AI 작업 중에도 문서 편집·자동 저장은 가능합니다. 공동 작업, 블록 드래그 이동, 이미지 업로드는 아직 지원하지 않습니다.

편집기 번들은 저장소에 포함되어 있어 Python 서버만으로 실행됩니다. 편집기 소스(`src/web/editor/editor.js`) 수정 시에만 Node.js로 다시 빌드하세요.

```powershell
npm ci
npm run build:editor
```

Markdown 입출력은 [Tiptap Markdown](https://tiptap.dev/docs/editor/markdown/api/editor)을 사용합니다. 정확한 서식 복원에는 함께 저장하는 JSON을 사용합니다.

1. 오른쪽 채팅에 대상 사용자와 프로젝트 아이디어를 입력합니다.
2. 추가 질문이 나타나면 선택하거나 직접 작성해 제출합니다.
3. 생성 중에는 단계 상태와 문서를 주기적으로 갱신합니다. 기존 그래프의 `Refresh` 단계는 자동으로 계속 실행합니다.
4. 문서와 리서치 자료를 확인하고 Markdown 파일을 다운로드합니다. 추가 요청은 채팅으로 전달합니다.

대시보드는 로컬 단일 프로세스용입니다. `--workers`는 늘리지 마세요. 세션은 메모리에 저장되므로 브라우저 새로고침 시 복구되지만 서버 재시작 시 초기화됩니다. 생성 파일은 기존 에이전트의 `output/`에 남습니다. 공유 벡터 저장소와 파일을 사용하는 기존 에이전트 작업은 한 번에 하나씩 실행합니다. Mermaid 코드 및 로컬 이미지 파일은 현재 미리보기에서 시각화하지 않으며, 원문은 Markdown 다운로드에 포함됩니다.

## 검증

```powershell
uv run pytest tests/test_dashboard.py tests/test_evaluation.py -q
uv run python tests/dashboard_browser_smoke.py
```

대시보드 테스트는 모델 호출을 대체해 세션 분리, 응답 검증, 반복 단계, 오류 시 상태 보존, 문서 다운로드 및 HTML 이스케이프를 검증합니다. 실제 생성에는 실행 중인 모델 서버가 필요합니다.
