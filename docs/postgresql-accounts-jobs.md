# 계정·문서 버전·Job 운영

Google OAuth 실제 연결·검증은 현재 보류한다. 코드와 설정 예시는 유지하되,
클라이언트 설정이 없는 기본 환경에서는 비밀번호 로그인을 사용한다.

현재 구현은 단일 API 프로세스 기준이다. Google 외의 OAuth 공급자는 아직 구현하지 않았다.
계정·Job·문서 버전은 `002_history_auth`로 추가된다. 기존 최신 초안과 AI 결과를 최초
이력으로 복사하며 기존 문서를 삭제하지 않는다. 버전은 성공한 저장마다 생성되며 자동 삭제하지 않는다.
이전 버전 복원은 새 초안 버전을 만든다. 생성 결과는 초안을 자동 덮어쓰지 않는다.

## 사용자 실행: 환경과 초기 관리자

의존성 설치는 사용자가 직접 실행한다. 설치 위치는 `.venv`이며 다운로드 크기는 환경에 따라 다르다.

```bash
uv sync
.venv/bin/python -c "import authlib, argon2, itsdangerous; print('OK')"
```

`.env`에 `AUTH_SECRET`(32자 이상 임의 문자열), `APP_BASE_URL=http://127.0.0.1:8000`을 설정한다.
키 생성 예: `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`.
실제 키·비밀번호는 Git에 넣지 않는다. 마이그레이션 적용 전 기존 DB를 백업한다.

초기 관리자는 `.env`에서 관리한다. 서버가 시작될 때마다 DB와 동기화한다.

```bash
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=<4자 이상>
```

- 계정이 없으면 관리자로 생성하고, 기존 로컬 개발 문서(`local` 소유)를 한 번 인계한다.
- `ADMIN_PASSWORD`를 바꾸면 다음 시작 때 비밀번호가 바뀌고 기존 로그인 세션이 모두 끊긴다.
- 관리자 권한·활성 상태가 해제돼 있으면 다시 켠다.
- `ADMIN_EMAIL`을 바꾸면 새 관리자가 생기며 이전 계정은 삭제·강등하지 않는다.
- 두 값 중 하나만 있거나 비밀번호가 4자 미만이면 서버가 시작되지 않는다. 둘 다 비우면 동기화를 건너뛴다.

```bash
uv run alembic upgrade head
```

추가 계정은 CLI로 만든다. 명령은 비밀번호를 숨김 입력으로 받는다. CLI는 서버를 관리할
수 있는 운영자가 실행하며 공개 회원가입 API는 제공하지 않는다. `.env` 대신 CLI로 관리자를
만들 때는 `--admin --adopt-local`로 기존 로컬 문서를 명시적으로 인계할 수 있다.

```bash
PYTHONPATH=src uv run python -m storage.accounts admin@example.com --admin --adopt-local
```

```bash
PYTHONPATH=src uv run python -m storage.accounts member@example.com
PYTHONPATH=src uv run python -m storage.accounts google-user@gmail.com --google-only
```

비밀번호 계정에 Google도 허용하려면 생성 시 `--allow-google`을 사용한다.
Google 연결은 관리자가 명시적으로 허용한 이메일만 가능하며, 연결 후에는 Google의
고유 subject로 식별한다. 일반 비밀번호 계정은 같은 이메일이라고 자동 연결하지 않는다.
추가 외부 로그인 공급자는 공급자별 검증 설정을 별도로 구현해야 한다.

## Google 설정: 사용자 실행

Google Cloud Console에서 OAuth 웹 애플리케이션 클라이언트를 생성한다.
로컬 승인된 리디렉션 URI: `http://127.0.0.1:8000/api/auth/google/callback`.
동의 화면 테스트 사용자에 로그인할 계정을 등록한다.
`.env`의 `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`에 값을 입력하고 앱을 재시작한다.
배포 시 `APP_BASE_URL`과 등록된 콜백을 HTTPS 주소로 함께 변경한다.
설정이 없으면 Google 버튼은 숨기고 비밀번호 로그인을 사용한다.

OAuth state/nonce·PKCE와 ID 토큰 검증은 Authlib을 사용한다.
로그인 세션은 12시간 유효한 HttpOnly/SameSite 쿠키이며 DB에는 토큰 해시만 저장한다.
상태 변경 API는 CSRF 헤더를 검사한다. HTTPS 주소에서는 Secure 쿠키를 사용한다.

공식 참고: https://developers.google.com/identity/openid-connect/openid-connect

## 버전·Job

- 초안 저장은 기존 `base_revision` 조건을 유지한다. 이력은 문서별로 소유자를 확인한다.
- AI 요청에는 `Idempotency-Key`가 필요하다. 같은 키·입력은 기존 Job을 반환하고 다른 입력은 409다.
- 실패 후 새 시도는 새 요청 키를 사용한다. 자동 재시도는 하지 않는다.
- 서버 재시작 시 실행 중 Job·agent_runs를 interrupted로 기록하고 문서는 보존한다.
- 로그인 뒤 화면의 ‘버전·실행 이력’에서 최근 20개를 확인한다. API는 limit/offset을 지원한다.
- 기존 파일 가져오기는 `--owner-email`을 반드시 지정한다.

## 검증과 백업

전용 `_test` DB에 마이그레이션을 적용한 뒤 `TEST_DATABASE_URL`을 설정하고 pytest를 실행한다.
GitHub Actions는 PR 또는 수동 실행 시 실제 PostgreSQL을 사용한다. 이 문서 작성 과정에서는
외부 의존성 설치나 원격 CI 실행을 자동 수행하지 않는다.

백업은 매일 및 마이그레이션 직전에 `pg_dump -Fc`로 생성한다. 최근 7일 일간본과
최근 4주 주간본을 프로젝트 밖의 접근 제한된 별도 저장소에 보관한다. 로컬 `output/backups`
파일만으로는 장치 장애를 복구할 수 없으므로 운영자가 별도 사본을 관리한다.
매월 새 복원 DB에 `pg_restore --exit-on-error` 후 사용자·문서·버전·Job 건수와 내용을
확인하고, 마이그레이션 버전·사용자 격리·샘플 문서 조회를 검증한다. 운영 DB에 덮어쓰지 않는다.
실제 백업 스케줄러·외부 보관 위치는 배포 환경에서 설정해야 한다.
