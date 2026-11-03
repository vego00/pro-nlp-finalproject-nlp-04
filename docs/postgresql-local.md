# 로컬 PostgreSQL 실행

Windows에 PostgreSQL을 설치하지 않고 Docker Desktop으로 실행한다.
Compose는 DB 실행 환경을 제공하며, 앱의 세션·문서 저장은 아래 마이그레이션 적용 후 사용할 수 있다.

## 최초 준비

Docker Desktop의 Settings → Resources → WSL Integration에서 **Ubuntu**를 켜고 Apply 한다.
General에 `Use WSL 2 based engine` 항목이 있으면 활성화한다.
이후 Ubuntu 터미널의 프로젝트 루트에서 확인한다.

```bash
docker version
docker compose version
```

`.env`가 없으면 `.env.example`을 복사한다. 기존 `.env`는 덮어쓰지 않는다.
`POSTGRES_PASSWORD`(관리자)와 `APP_DB_PASSWORD`(앱)에 서로 다른 임의 비밀번호를 설정한다.
향후 앱 연결용 `DATABASE_URL`은 `.env.example`의 형식을 참고해 설정한다.
`.env`는 Git에서 제외되므로 각 개발 환경에서 위 값을 준비해야 한다.

## 실행 및 확인

```bash
docker compose config --quiet
docker compose up -d --wait postgres
docker compose ps
docker compose exec postgres sh -c 'PGPASSWORD="$APP_DB_PASSWORD" psql -h 127.0.0.1 -U "$APP_DB_USER" -d "$POSTGRES_DB" -c "SELECT current_database(), current_user;"'
```

기본 접속 주소는 `127.0.0.1:5432`, DB는 `div`, 앱 계정은 `div_app`이다.
앱 계정에는 슈퍼유저 권한 없이 `public` 스키마에서 테이블을 만들 수 있는 권한을 부여한다.
관리자 계정은 `postgres`다. 호스트 포트가 이미 사용 중이면 `.env`의
`POSTGRES_PORT`와 `DATABASE_URL`의 포트를 함께 변경한다.

초기 계정 생성 스크립트와 `POSTGRES_*` 초기화 값은 **빈 볼륨에서 처음 실행할 때만** 적용된다.
기존 DB의 비밀번호는 `.env`만 수정해도 바뀌지 않는다. SQL로 계정을 변경하고 연결 설정도 맞춰야 한다.

## 중지와 데이터 보존

```bash
docker compose stop postgres
docker compose start postgres
```

데이터는 Docker named volume `div-local_postgres_data`에 저장된다.
`docker compose down`으로 컨테이너를 제거해도 유지된다.
**`docker compose down -v`는 DB 볼륨과 데이터를 삭제하므로 사용하지 않는다.**
PostgreSQL 메이저 버전을 바꿀 때는 별도 마이그레이션이 필요하다.

## 백업

프로젝트 루트에서 실행한다. `output/`은 Git에서 제외된다.

```bash
mkdir -p output/backups
docker compose exec -T postgres sh -c 'pg_dump -U postgres -d "$POSTGRES_DB" -Fc' > "output/backups/div-$(date +%Y%m%d-%H%M%S).dump"
```

볼륨은 백업을 대신하지 않는다. 복원 검증은 별도 DB에서 진행해야 한다.

공식 안내: [Docker Desktop WSL 연결](https://docs.docker.com/desktop/features/wsl/),
[PostgreSQL 이미지와 초기화 설정](https://hub.docker.com/_/postgres).

## 애플리케이션 저장 기능

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn web.app:app --app-dir src --host 127.0.0.1 --port 8000
```

`.env`의 `DATABASE_URL`이 필요하다. 마이그레이션은 앱 시작 전에 명시적으로 실행한다.
앱은 단일 프로세스(`--workers 1`)로 실행한다. 로그인 없는 로컬 개발용이며,
고정 개발 사용자 소유로 문서·초안·대화·AI 결과를 PostgreSQL에 저장한다.
서버 시작 시 미완료 AI 요청은 중단 오류로 표시하며 자동 재실행하지 않는다.

기존 파일 가져오기(원본 보존, 기존 ID는 건너뜀):

```bash
PYTHONPATH=src uv run python -m storage.import_drafts output/drafts --owner-email admin@example.com --dry-run
PYTHONPATH=src uv run python -m storage.import_drafts output/drafts --owner-email admin@example.com
```

DB 통합 테스트는 `TEST_DATABASE_URL`에 별도 `_test` DB를 설정한다.
그 DB에 먼저 마이그레이션을 적용한 뒤 `uv run pytest -q`를 실행한다.
테스트는 해당 DB의 세션·문서·개발 사용자 데이터를 초기화한다.
변수가 없으면 DB 통합 테스트를 건너뛴다.

Windows Edge 브라우저 테스트는 기존 명령을 사용한다. Linux Chromium 환경에서는
`BROWSER_CHANNEL='' uv run python tests/dashboard_browser_smoke.py`로 실행한다.

프로세스 강제 종료·재시작 및 브라우저 검증을 함께 실행하려면, 마이그레이션이
적용된 전용 `TEST_DATABASE_URL`을 설정한 뒤 다음 명령을 실행한다.
테스트 API는 사용 가능한 임시 포트에서 실행 후 종료되며, 테스트 문서가 DB에 남는다.

```bash
uv run python tests/dashboard_restart_smoke.py
```

Linux에서는 설치한 Chromium을 쓰도록 `BROWSER_CHANNEL=''`을 지정할 수 있다.

계정·버전·Job 단계에서는 [초기 관리자와 로그인 설정](postgresql-accounts-jobs.md)을 먼저 완료해야 한다.
브라우저 테스트는 테스트 계정의 `TEST_LOGIN_EMAIL`, `TEST_LOGIN_PASSWORD`를 요구한다.
재시작 스모크 스크립트는 전용 테스트 DB에 임시 계정을 자동 생성한다.
