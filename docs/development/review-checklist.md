# 코드 리뷰 체크리스트

- 작성일: 2026-10-22 (원본), Django 이식: 2026-10-24
- 관련: [명명 규칙과 용어집](naming.md), [이식 계획 2절](../../porting/porting-plan.md#2-기본-원칙)

PR 설명에 해당 없는 항목은 "해당 없음"으로 표시한다. 자동 검사로 확인되는 항목은 (CI)로 표시했다.

## 1. 자동 검사

- [ ] `uv run ruff format --check`, `uv run ruff check` 통과 (CI)
- [ ] `uv run mypy ninefruits config tools/checks` 통과 (CI)
- [ ] `uv run tools/checks/raw_sql.py`(원시 SQL 검사), `uv run manage.py naming_check`(명명 검사), `uv run manage.py i18n_missing --strict`(번역 누락) 통과 (CI)
- [ ] `uv run pytest -n auto -m "not concurrency"`, `uv run pytest -m concurrency` 통과 (CI)
- [ ] `uv run bandit -q -c pyproject.toml -r ninefruits --severity-level medium`, `pip-audit --strict`(`uv export`로 만든 목록) 경고 없음 (CI)
- [ ] `uv run manage.py makemigrations --check --dry-run` 변경 없음, `uv run manage.py check` 통과
- [ ] 새 관리 명령은 `docs/manual/{ko,en,zh_Hans,lo}/operations/commands.md`에 `### \`명령\`` 항목이 있다 (CI, `tests/tooling/test_command_documentation.py`)

## 2. 명명

- [ ] 새 용어는 [용어집](naming.md#6-용어집)에 먼저 추가했다
- [ ] 테이블/컬럼/권한/URL/번역이 [명명 규칙](naming.md)을 따른다 (테이블과 컬럼, 마이그레이션·명령 이름, msgid는 `naming_check`로 확인)
- [ ] 레거시 이름(`SFOP_`, `SEMECNT`, 병음 파일명 등)을 그대로 옮기지 않았다

## 3. 데이터베이스

- [ ] 스키마는 바꾸지 않았다. 모델은 기존 테이블과 정확히 맞고(`db_table`, `db_column`, `null`, 길이, 타입, FK), `makemigrations`가 상태 전용 마이그레이션만 만들었다 (`tests/db/test_model_schema.py`, `tests/db/test_schema_equivalence.py`)
- [ ] 함수/트리거/정책/뷰는 `db/sql/` 파일로 관리하고 `SqlFile`로 적용한다
- [ ] 시각은 `timestamptz`, 날짜는 `date`, 기간은 `daterange`/`tstzrange`다. 문자열 날짜가 없다
- [ ] 다국어 값은 `jsonb` 한 컬럼 + `CHECK (jsonb_typeof(col) = 'object')`, 모델은 `TranslatableJSONField`
- [ ] 학적/성적 등 이력이 중요한 테이블은 `util.enable_audit()`를 적용했고, 비밀 컬럼은 마스킹 목록에 넣었다
- [ ] RLS 대상 테이블은 정책이 있고 [정책 작성 규칙](../../porting/porting-plan.md#74-행-단위-보안)(함수는 `(SELECT ...)`로 감싸기)을 따랐다
- [ ] 백업용 테이블이나 `_old`, 날짜 접미사 테이블을 만들지 않았다

## 4. 보안

- [ ] 원시 SQL은 상수 문자열과 바인딩 파라미터만 쓴다. 정렬/필터 컬럼은 허용 목록으로 받는다. `.extra()`는 쓰지 않는다 (CI)
- [ ] 권한은 카탈로그(`ninefruits.security.enums.Permission`)에 추가하고 라벨 번역을 넣었다. Django `auth.Permission`/`Group`, 슈퍼유저는 쓰지 않는다
- [ ] 화면(ModelAdmin `get_queryset`, 포털 뷰, API viewset)은 `visible_to(user)`나 정책(`user.has_perm(perm, obj)`)을 거친다. ModelAdmin은 `CatalogAdmin`의 `permissions`로 권한을 정한다
- [ ] 역할별 접근 테스트가 있다 (다른 학생의 URL을 직접 호출하면 403 등)
- [ ] 개인정보는 `EncryptedPiiField` + `*_encrypted`/`*_hash` 컬럼, 화면은 마스킹, 표시 해제는 기록을 남기는 Action으로. `__repr__`, 로그, serializer, admin 목록에 평문이 없다
- [ ] 직무 분리 규칙(요청자는 승인 불가 등)을 정책에 반영했다
- [ ] 대량 내보내기는 권한, 사유, 보안 로그(`data.exported`)를 남긴다
- [ ] 템플릿의 `<script>`에는 `nonce="{{ csp_nonce }}"`가 있고 인라인 이벤트 처리기(`onclick=`, `hx-on`)가 없다. Alpine은 CSP 빌드용 `Alpine.data()` 컴포넌트로 쓴다
- [ ] 상태를 바꾸는 요청은 POST(+CSRF)다. HTMX 요청은 `hx-headers`의 CSRF 토큰을 쓴다

## 5. 구조

- [ ] 업무 로직은 Action(`ninefruits/{app}/actions/`)에 있고 admin, 포털 뷰, API, 명령은 Action을 호출만 한다
- [ ] 검증은 Django `Form`/`ModelForm` 또는 DRF serializer, 권한은 정책/인증 백엔드
- [ ] 상태값은 `TextChoices`/`StrEnum`, 설정은 `settings` 앱 그룹(`SettingsGroup.load()`)이나 `django.conf.settings`로만 읽는다 (`env()`는 `config/settings/` 안에서만)
- [ ] 학적/성적 변경, 권한 변경 등 업무 감사 대상은 `ninefruits.audit`로 사유와 함께 기록한다
- [ ] Celery 작업은 멱등이고 `SystemTask`를 상속한다. 중복 실행 방지가 필요하면 Redis 잠금을 쓴다. DB 변경 뒤 넣는 작업은 `transaction.on_commit`
- [ ] 데이터를 바꾸는 명령은 `AuditedCommand`를 상속한다(`--actor`, `--dry-run`, 종료 코드 0/1/2)
- [ ] 지연 로딩이 없다(django-seal), 목록은 `select_related`/`prefetch_related`로 미리 불러온다
- [ ] 관리 화면 메뉴 위치는 `navigation_group`(또는 앱 기본 묶음), 맞춤 화면은 `site.register_view(...)` 또는 `register_link(...)`, 포털 메뉴는 `ninefruits.portal.menu.register(...)`로 추가한다

## 6. 다국어

- [ ] 화면 문구는 gettext(`_()`, `{% translate %}`)이고 msgid는 영어 원문이다. 같은 영어가 다르게 번역돼야 하면 `pgettext("{원본 그룹}", ...)`
- [ ] `ko`, `zh_Hans`, `lo` 번역을 모두 넣었다 (`uv run manage.py i18n_missing --strict`, CI)
- [ ] 날짜와 숫자는 사용자 로케일로 표시한다 (`nf_i18n`의 `ll`, `lll`, `number` 필터)
- [ ] 관리자 매뉴얼 해당 장과 운영 매뉴얼을 한국어로 먼저 고치고 4개 언어를 맞췄다. 매뉴얼의 상대 링크와 언어별 파일 목록은 `tests/tooling/test_command_documentation.py`가 검사한다 (CI)
- [ ] 화면이 크게 바뀌었으면 README 스크린샷을 다시 찍었다(`uv run python tools/screenshots.py`, [언어 추가 가이드 4절](adding-a-language.ko.md#4-문서))

## 7. 테스트

- [ ] 경로: `tests/{app 또는 영역}/test_{대상}.py`, DB 계층은 `tests/db/`. 원본 테스트와 같은 경우를 옮기고 `porting/test-mapping.md`를 갱신했다
- [ ] 데이터는 팩토리(`tests/factories/`)로 만든다. 레거시 실데이터나 실제 개인정보를 쓰지 않는다
- [ ] DB 오류를 기대하는 테스트는 `transaction.atomic()` 세이브포인트 안에서 실행한다
- [ ] 다른 사람과 동시에 돌릴 때는 자기 테스트 DB를 쓴다(`DB_TEST_DATABASE=test_nf_<이름> uv run pytest --reuse-db`)
