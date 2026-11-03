# Docker Ollama와 향후 Colab GPU 연결

현재는 Docker Desktop의 Ollama를 CPU로 실행한다. GPU 추론은 향후 Colab SSH
연결을 사용할 예정이며, 앱은 `OLLAMA_BASE_URL`로 사용할 서버를 선택한다.

Compose의 Ollama 이미지는 검증한 0.40.13의 digest로 고정했다.
업데이트할 때는 새 이미지와 모델 호환성을 확인한 뒤 digest를 변경한다.

## 로컬 실행

Docker Desktop을 실행한 뒤 프로젝트 루트에서 다음 명령을 실행한다.
PostgreSQL 비밀번호 등 `.env` 준비는 [PostgreSQL 안내](postgresql-local.md)를 참고한다.

```bash
docker compose up -d --wait
docker compose exec ollama ollama pull qwen3.5:4b
# 고사양 GPU 환경에서 Qwen/Qwen3.8-27B를 사용할 때(선택):
# docker compose exec ollama ollama pull qwen3.8:27b
docker compose exec ollama ollama list
```

`.env`의 기본 설정 (`qwen3.8:27b`로 변경 가능):

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=qwen3.5:4b
LLM_MINI_MODEL=qwen3.5:4b
OLLAMA_PORT=11434
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

본 모델과 보조 모델을 다르게 설정하면 두 모델을 각각 내려받아야 한다.
컨테이너의 healthy 상태는 서버 응답만 확인한다. 모델 설치 여부는
앱의 연결 확인(`/api/health`) 또는 `ollama list`로 확인한다.

모델은 `div-local_ollama_data` named volume에 보관한다. 재시작이나 컨테이너
재생성 후에도 유지된다. `docker compose down -v`는 모델과 PostgreSQL 데이터
볼륨을 모두 삭제하므로 사용하지 않는다. CPU에서 큰 기획 요청은 오래 걸릴 수 있다.

```bash
docker compose stop ollama
docker compose start ollama
docker compose logs --tail=50 ollama
```

Windows에 따로 설치한 Ollama가 같은 포트를 사용하면 해당 서버를 종료하거나
`OLLAMA_PORT`와 `OLLAMA_BASE_URL`을 함께 변경한다. FastAPI는 현재 WSL에서 직접
실행하므로 로컬 공개 포트에 연결한다.

## 향후 Colab GPU 서버로 전환

Colab 공식 FAQ는 무료 관리형 런타임의 SSH 원격 제어를 제한하며, 유료 플랜과
양수의 컴퓨팅 유닛 잔액을 관련 제한 해제 조건으로 안내한다.
사용 환경은 [Colab FAQ](https://research.google.com/colaboratory/faq.html)를 확인한다.

Colab 쪽 SSH 접속과 Ollama GPU 서버를 먼저 준비해야 한다. 아래는 연결 정보가
준비된 후 **앱을 실행하는 WSL 터미널**에서 사용할 예시이며, 현재 연결된 상태는 아니다.
원격 Ollama는 원격 호스트의 `127.0.0.1:11434`에서 실행한다고 가정한다.

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:11435:127.0.0.1:11434 -p <SSH_PORT> <USER>@<SSH_HOST>
```

SSH 제공 방식에 따라 키나 ProxyCommand 등 추가 옵션이 필요할 수 있다.
동일한 포트 포워딩을 수행하는 로컬 스크립트도 제공한다.
아래 호스트·포트·키 경로는 실제 접속 정보로 교체한다.

```bash
bash scripts/colab-tunnel.sh -p 2222 -i ~/.ssh/colab_key user@ssh-host.example
```

첫 연결 때 표시되는 호스트 키 지문은 Colab 쪽에서 확인한 값과 대조한다.
호스트 키 검사를 끄거나 비밀번호·개인키를 저장소에 기록하지 않는다.
설치·모델 다운로드가 필요하면 사용자가 직접 실행한다. 이 스크립트는
다운로드나 설치를 수행하지 않으며, 터널은 Ctrl+C로 종료한다.

연결 후 WSL에서 API와 모델 목록을 확인한다(다운로드 명령이 아님).

```bash
curl --fail --max-time 5 http://127.0.0.1:11435/api/version
curl --fail --max-time 5 http://127.0.0.1:11435/api/tags
```

터널을 유지한 상태에서 `.env`를 변경하고 FastAPI를 재시작한다.

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11435
```

원격 서버에도 `LLM_MODEL`과 `LLM_MINI_MODEL`에 지정한 모델이 설치돼 있어야 한다.
로컬 Docker 볼륨의 모델은 Colab으로 자동 전송되지 않는다. Colab 세션·SSH 터널이
종료되면 앱 연결도 끊기며, 로컬 CPU 서버로 자동 전환하지 않는다.
로컬로 돌아올 때는 URL을 `http://127.0.0.1:11434`로 되돌리고 앱을 재시작한다.
원격 GPU만 사용할 때 로컬 Ollama는 `docker compose stop ollama`로 중지할 수 있다.

공식 참고: [Ollama Docker 실행](https://docs.ollama.com/docker),
[Docker Desktop GPU 지원 조건](https://docs.docker.com/desktop/features/gpu/).
