#!/usr/bin/env bash
# Start Docker services, apply DB migrations, and run the FastAPI dashboard.
# Default mode never downloads anything; pass --setup to run uv sync, pull
# missing Docker images, and pull missing Ollama models explicitly.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: bash scripts/run.sh [--setup] [--check] [--open]

  --setup   Install/download first: uv sync, docker images, Ollama models.
  --check   Run all checks and migrations, then exit without starting the server.
  --open    Open the dashboard in the default browser once the server responds.

Environment overrides: HOST (default 127.0.0.1), PORT (default 8000).
EOF
}

SETUP=0
CHECK_ONLY=0
OPEN_BROWSER=0
for arg in "$@"; do
    case "$arg" in
        --setup) SETUP=1 ;;
        --check) CHECK_ONLY=1 ;;
        --open) OPEN_BROWSER=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; usage >&2; exit 2 ;;
    esac
done

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Non-interactive shells (e.g. a Windows shortcut via wsl.exe) skip ~/.profile,
# so user-local tool directories such as ~/.local/bin may be missing.
for dir in "$HOME/.local/bin" "$HOME/.cargo/bin"; do
    if [[ -d "$dir" && ":$PATH:" != *":$dir:"* ]]; then
        PATH="$dir:$PATH"
    fi
done
export PATH

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# Read KEY from .env or src/config/.env without sourcing it (passwords may contain shell syntax).
env_value() {
    local key=$1 default=${2:-} line="" value f
    for f in src/config/.env .env; do
        if [[ -f "$f" ]]; then
            local match
            match=$(grep -E "^[[:space:]]*(export[[:space:]]+)?${key}=" "$f" | tail -n 1 || true)
            [[ -n "$match" ]] && line=$match
        fi
    done
    if [[ -z "$line" ]]; then
        printf '%s' "$default"
        return
    fi
    value=${line#*=}
    value=${value%$'\r'}
    value=${value#\"}; value=${value%\"}
    value=${value#\'}; value=${value%\'}
    printf '%s' "${value:-$default}"
}

# 1. Prerequisites
command -v docker >/dev/null || fail "docker를 찾을 수 없습니다. Docker Desktop의 WSL Integration을 확인하세요."
docker compose version >/dev/null 2>&1 || fail "docker compose를 사용할 수 없습니다."
command -v uv >/dev/null || fail "uv를 찾을 수 없습니다."

if [[ ! -f .env ]]; then
    fail ".env가 없습니다. 'cp .env.example .env' 후 POSTGRES_PASSWORD, APP_DB_PASSWORD, DATABASE_URL, AUTH_SECRET을 설정하세요."
fi
for key in POSTGRES_PASSWORD APP_DB_PASSWORD DATABASE_URL AUTH_SECRET; do
    [[ -n "$(env_value "$key")" ]] || fail ".env의 $key 값이 비어 있습니다."
done
admin_email=$(env_value ADMIN_EMAIL)
admin_password=$(env_value ADMIN_PASSWORD)
if [[ -z "$admin_email" && -z "$admin_password" ]]; then
    info "경고: .env에 ADMIN_EMAIL/ADMIN_PASSWORD가 없습니다. 기존 계정이 없으면 로그인할 수 없습니다."
elif [[ -z "$admin_email" || -z "$admin_password" ]]; then
    fail ".env의 ADMIN_EMAIL과 ADMIN_PASSWORD는 함께 설정해야 합니다."
elif (( ${#admin_password} < 4 )); then
    fail ".env의 ADMIN_PASSWORD는 4자 이상이어야 합니다."
fi

# 2. Python dependencies
if [[ $SETUP -eq 1 ]]; then
    info "uv sync"
    uv sync
elif [[ ! -d .venv ]]; then
    fail ".venv가 없습니다. 'bash scripts/run.sh --setup' 또는 'uv sync'를 먼저 실행하세요."
fi

# 3. Docker services (healthchecks are awaited by --wait)
info "docker compose up"
docker compose config --quiet
if [[ $SETUP -eq 1 ]]; then
    docker compose up -d --wait --pull missing
else
    docker compose up -d --wait --pull never \
        || fail "컨테이너 시작 실패. 이미지가 없다면 '--setup'으로 실행하세요. 로그: docker compose logs"
fi
docker compose ps

# 4. Ollama models (only when the dashboard uses the Docker Ollama)
provider=$(env_value LLM_PROVIDER ollama | tr '[:upper:]' '[:lower:]')
ollama_port=$(env_value OLLAMA_PORT 11434)
ollama_url=$(env_value OLLAMA_BASE_URL "http://127.0.0.1:11434")
ollama_url=${ollama_url%/}

if [[ "$provider" == "ollama" ]]; then
    case "$ollama_url" in
        "http://127.0.0.1:${ollama_port}"|"http://localhost:${ollama_port}")
            installed=$(docker compose exec -T ollama ollama list | awk 'NR > 1 { print $1 }')
            models=$(printf '%s\n%s\n' "$(env_value LLM_MODEL qwen3.5:4b)" "$(env_value LLM_MINI_MODEL)" | awk 'NF && !seen[$0]++')
            while IFS= read -r model; do
                if grep -qxF "$model" <<<"$installed" || grep -qxF "${model}:latest" <<<"$installed"; then
                    info "Ollama 모델 확인: $model"
                elif [[ $SETUP -eq 1 ]]; then
                    info "ollama pull $model"
                    docker compose exec -T ollama ollama pull "$model"
                else
                    fail "Ollama 모델 '$model'이 없습니다. 'docker compose exec ollama ollama pull $model' 또는 '--setup'으로 실행하세요."
                fi
            done <<<"$models"
            ;;
        *)
            info "OLLAMA_BASE_URL=$ollama_url (외부 Ollama) — 모델 확인을 건너뜁니다."
            ;;
    esac
fi

# 5. Database migrations
info "alembic upgrade head"
uv run --no-sync alembic upgrade head

if [[ $CHECK_ONLY -eq 1 ]]; then
    info "확인 완료 (--check). 서버는 시작하지 않습니다."
    exit 0
fi

# 6. Dashboard (single process; do not add --workers)
host=${HOST:-127.0.0.1}
port=${PORT:-8000}
url="http://${host}:${port}"
info "대시보드: ${url} (종료: Ctrl+C)"

if [[ $OPEN_BROWSER -eq 1 ]]; then
    (
        for _ in $(seq 1 60); do
            if (exec 3<>"/dev/tcp/${host}/${port}") 2>/dev/null; then
                if command -v explorer.exe >/dev/null; then
                    explorer.exe "$url" >/dev/null 2>&1 || true
                elif command -v xdg-open >/dev/null; then
                    xdg-open "$url" >/dev/null 2>&1 || true
                fi
                exit 0
            fi
            sleep 1
        done
    ) &
fi
exec uv run --no-sync uvicorn web.app:app --app-dir src --host "$host" --port "$port"

