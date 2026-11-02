# 로컬 PostgreSQL 실행

Windows에 PostgreSQL을 설치하지 않고 Docker Desktop으로 실행한다.
현재 Compose 구성은 DB 실행 환경을 제공하며, 앱의 세션·문서 저장은 아직 DB와 연결되지 않았다.

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
