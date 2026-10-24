# Phase 0 CI 메모

- 작성일: 2026-10-24
- 관련: [이식 계획 16절](porting-plan.md#16-ci), `.github/workflows/ci.yml`

## 1. 실행 여부

이 작업 환경에서는 GitHub Actions를 실행할 수 없었다(원격 저장소에 푸시하지 않음, Actions 러너 없음). 워크플로 파일은 YAML 구문만 확인했고, 각 단계의 명령은 같은 서비스(PostgreSQL 18, Redis 8, Gotenberg 8)가 있는 로컬 환경에서 따로 실행해 결과를 아래에 적었다. 원본 Phase 0과 같이 첫 원격 실행은 저장소를 만든 뒤에 확인한다.

Docker 이미지(`Dockerfile`)도 끝까지 빌드하지 못했다. 이 환경의 빌드 컨테이너는 외부 네트워크(Debian 패키지 저장소, ghcr.io)에 접근할 수 없다. `docker compose config`로 `compose.yaml` 구문은 확인했다. uv는 ghcr.io 이미지 대신 PyPI(`pip install uv==0.11.32`)로 설치하도록 했다(이 환경에서 `uv.lock`을 다루는 uv와 같은 버전).

## 2. Job 구성

| Job | 단계 |
|---|---|
| 품질(`quality`) | `uv sync --frozen`, `ruff format --check`, `ruff check`, `mypy ninefruits config tools/checks`(비차단), `bandit -q -r ninefruits --severity-level medium`, `pip-audit`(`uv export` 결과, 해시 포함), `tools/checks/raw_sql.py`, DB 역할 생성(`db/sql/roles/create_roles.sql`) → `migrate`, `manage.py check`, `makemigrations --check --dry-run`, `naming_check`(실제 DB 카탈로그를 읽으므로 PostgreSQL 서비스 필요), `i18n_missing --strict`, `npm ci && npm run build` |
| 테스트(`tests`) | 서비스 `postgres:18-alpine`, `redis:8-alpine`, `gotenberg/gotenberg:8`. 역할 생성 SQL → `compilemessages` → `pytest -n auto -m "not concurrency"` → `pytest -m concurrency`. 매뉴얼 검사(명령 문서화, 상대 링크, 언어 간 파일 목록)는 `tests/tooling/`에 있어 이 job에서 함께 돈다 |

테스트 DB는 테스트 세션이 슈퍼유저로 만들고 `app_migrator`로 마이그레이션한다(`tests/conftest.py`). 그래서 CI는 클러스터 역할만 먼저 만든다.

## 3. 로컬 실행 결과 (2026-10-24, Phase 0 작업 종료 시점)

| 단계 | 결과 | 메모 |
|---|---|---|
| `ruff format --check`, `ruff check` | 통과 | |
| `mypy` | 75건(29개 파일) | 대부분 django-stubs/unfold 타입(`Any` 상속, `handle` 반환형 등). strict 결과가 정리될 때까지 `continue-on-error: true`로 비차단. 정리되면 차단으로 바꾼다 |
| `bandit` | medium 이상 0건 | low 7건은 모두 B105(문자열 상수 `password.reset` 등을 비밀번호로 오인). 그래서 `--severity-level medium` |
| `pip-audit` | 취약점 0건 | `--disable-pip`는 해시가 있는 requirements가 필요해 `uv export`에 `--no-hashes`를 쓰지 않는다 |
| `npm audit --omit=dev` | 0건 | |
| `raw_sql.py` | 위반 0건 | |
| `naming_check` | 위반 0건 | |
| `npm ci && npm run build` | 성공 | `static/dist/manifest.json` 생성. htmx의 `eval` 경고는 `htmx.config.allowEval = false`로 실행 경로가 막혀 있다 |
| `i18n_missing --strict` | 통과 | ko, zh_Hans, lo 누락 0 |
| `manage.py check`, `makemigrations --check --dry-run` | 통과 | |
| `pytest` (전체, 직렬) | 370 통과 | `-n auto`와 `-m concurrency` 분리 실행은 CI에서 확인 |

## 4. 남은 일

- 원격 저장소에서 첫 실행, 소요 시간 확인, 실패 단계 정리.
- mypy 차단 전환(정리 후 `continue-on-error` 제거).
- 운영 이미지 빌드 검증(네트워크가 되는 환경에서 `docker build --target production .`).
