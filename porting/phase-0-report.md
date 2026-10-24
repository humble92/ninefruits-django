# Phase 0 기반 구축 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 0](porting-plan.md#phase-0-기반-구축-l), 원본 [Phase 0 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-0-report.md)

## 1. 요약

Phase 0 작업 항목을 모두 구현했다. 테스트 370개 통과(직렬 17초, `-n 4` 10초). ruff format/check, raw SQL 검사, `manage.py check`, `makemigrations --check`, `naming_check`, `i18n_missing --strict`(ko, zh_Hans, lo) 모두 통과. GitHub Actions는 이 환경에서 원격 실행이 불가해 로컬에서 같은 검사를 돌렸다([CI 메모](phase-0-ci-notes.md)).

가장 큰 결정은 [ADR 0001-django](decisions/0001-django-schema-from-original-ddl.md): 원본 v1.0.0을 PostgreSQL 18.6에서 실제로 실행해 각 마이그레이션이 보낸 DDL을 기록하고, Django `core` 마이그레이션 48개가 이를 그대로 재생한다. 그 결과 **스키마 동등성 검사가 Phase 0부터 통과**한다(카탈로그 지문 3,650줄 일치). 도메인 앱 마이그레이션은 상태 전용이다.

## 2. 완료 기준

| 완료 기준 | 결과 | 근거 |
|---|---|---|
| 2단계 인증 정책 변경 즉시 반영 | 충족 | `tests/security/test_mfa_policy.py`, `test_settings_pages.py`(설정 화면으로 변경 후 다음 요청에서 등록 화면 이동) |
| 역할·할당 변경만으로 메뉴와 데이터 범위 변경 | 충족 | `tests/security/test_authorization.py`, `tests/admin/test_admin_panel.py`(사이드바가 권한별로 바뀜) |
| 트리거 감사가 외부 변경 기록 | 충족 | `tests/audit/test_audit_trigger.py`(ORM 밖 INSERT, 비밀 열 마스킹, 소유자도 수정 불가) |
| RLS가 다른 사용자 조회를 DB에서 차단 | 충족 (원본 PoC 테이블) | `tests/audit/test_row_level_security.py`. 실제 업무 테이블은 Phase 2부터 |
| 해시 체인 검증 통과 | 충족 | `tests/audit/test_audit_chain.py`, `audit_verify_chain` 종료 코드 2 |
| CI 통과 | 부분 | `.github/workflows/ci.yml` 작성, 같은 검사를 로컬에서 통과. 원격 실행 기록 없음 |
| (추가) 스키마 동등성 | 충족 | `tests/db/test_schema_equivalence.py`, `tests/db/test_model_schema.py` |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 저장소 골격 | Python 3.14.6, Django 6.1.2, uv, 설정 4종(base/local/test/production), Docker Compose, Dockerfile, pre-commit, CI 2 job | `pyproject.toml`, `config/`, `compose.yaml` |
| DB | 원본 DDL 재생(48개), 역할 3개, 연결 2개, `migrate`/`showmigrations`/`flush` 래퍼, 테스트 DB(슈퍼유저 생성 → 마이그레이터 마이그레이션 → 런타임 실행), 연결 풀 `reset` 콜백 | `ninefruits/core/{db,provision,schema}.py`, `db/` |
| 미들웨어 5개, 요청 컨텍스트 | contextvars 요청 컨텍스트, DB 세션 컨텍스트(요청 종료·`request_finished`·풀 반환 3중 초기화), JSON 로그 | `ninefruits/core/middleware.py`, `security/middleware.py`, `i18n/middleware.py` |
| 인증 | django-allauth + 자체 2단계 단계(TOTP, 복구 코드, 이메일 코드), 기기 기억, 정책 강제, 계정 잠금, 동일 실패 메시지, 학번 로그인 백엔드 | `ninefruits/security/` |
| 권한 | 카탈로그 63개, Role/RoleAssignment/UserIdentity, `CatalogPermissionBackend`, `AuthorizationService`, `PersonaResolver`(판정 규칙은 Phase 2), 직무 분리, admin 공통 mixin, 사용자·역할 관리 화면 | `ninefruits/security/`, `ninefruits/adminpanel/` |
| 감사 3층 + 해시 체인 | 비관리 모델(`'audit"."x'` 기법을 테스트로 고정), `audit()`, `record_security_event()`, `AuditedCommand`, 봉인·검증·정리 서비스와 명령, 조회 화면 3개 | `ninefruits/audit/`, `ninefruits/core/commands.py` |
| PII | 원본과 **같은 암호문 형식**(PHP↔Python 상호 복호화 테스트), HMAC 검색 해시, 마스킹, 표시 해제 기록, 재암호화 작업 | `ninefruits/pii/` |
| 파일 | Media 모델, 비공개 저장, MIME 검사, SHA-256, 권한 확인 다운로드 기반 | `ninefruits/media/` |
| 다국어 | gettext(영어 msgid, 원본 그룹을 `pgettext` 문맥으로), 앱별 카탈로그, `TranslatableJSONField`, `I18n()`/`I18nSearchText()`, 라오어 로케일·형식 추가, 변환 도구, `i18n_missing/export/import/makemessages` | `ninefruits/i18n/`, `tools/convert_translations.py` |
| 설정 | pydantic 설정 그룹, 데이터 마이그레이션(Security, Authentication, Institution, 라오어 추가), 설정 화면 기반 + 3개 화면 | `ninefruits/settings/`, `security/settings_pages.py` |
| PDF | Gotenberg 클라이언트(httpx), 레이아웃, `pdf_sample`(한·중·영·라오 혼합, Noto CJK KR/SC, Noto Sans Lao 포함 확인) | `ninefruits/pdf/` |
| 포털 골격 | 레이아웃(CSP nonce, HTMX CSRF 헤더), 메뉴 등록기, 대시보드, 보안 설정 화면 | `ninefruits/portal/`, `templates/` |
| 프런트엔드 | Vite 8 + Tailwind 4 + HTMX 2 + Alpine 3(CSP 빌드), django-vite | `frontend/`, `package.json` |
| 도구 | raw SQL AST 검사, `naming_check`(실제 DB 카탈로그 대상), 명령 문서화·매뉴얼 링크·언어 간 파일 목록 테스트 | `tools/checks/`, `tests/tooling/` |
| 명령 | 계획의 10개 + 앞당긴 8개: `security_create_administrator`, `security_sync_permissions`, `pii_generate_key`, `pii_reencrypt`, `i18n_missing`, `i18n_export`, `i18n_import`, `naming_check`, `pdf_sample`, `migrate`(래퍼), `security_reset_mfa`, `security_unlock_user`(Phase 2 예정분), `audit_seal`, `audit_verify_chain`, `audit_prune`, `media_prune_orphans`(Phase 13 예정분), `i18n_makemessages`, `createsuperuser`(비활성화) | `docs/manual/*/operations/commands.md` |
| 매뉴얼 | 4개 언어 골격, 관리자 1~4장, 운영 설치·명령·보안 키, README 4개 언어, 개발 문서(명명, 리뷰 체크리스트, 언어 추가) | `docs/` |

## 4. 계획과 달라진 점

| 항목 | 계획 | 실제 | 이유 |
|---|---|---|---|
| 스키마 생성 | ORM 가능한 것은 ORM, 나머지 `RunSQL` | 원본 DDL 전체 재생 + 상태 전용 마이그레이션 | 제약·인덱스 이름까지 동일해야 함. [ADR 0001-django](decisions/0001-django-schema-from-original-ddl.md) |
| 사용자 테이블 | 2단계 열이 원본과 달라짐(예외) | 원본과 동일. Fortify 열은 남기고 사용하지 않음 | 위 결정의 결과 |
| 다형 참조 | 언급 없음 | `subject_type`/`model_type`에 Django 모델 레이블(`person.person`) | [ADR 0002-django](decisions/0002-django-polymorphic-types.md), PHP 클래스명 대응표 포함 |
| 번역 카탈로그 위치 | `locale/` 한 곳 | 앱별 `ninefruits/<app>/locale/` + 전역 `locale/`(템플릿, Django·allauth·unfold 보완) | 병렬 작업 충돌 방지, Django 관례 |
| 기기 기억 | allauth trust | 자체 구현 | 기간을 설정에서 읽고 재등록·관리자 초기화 시 무효화 |
| 이메일 인증 | 필수 | 로그인에는 선택, 지원에 필수 | 원본 동작과 같음 |
| 지원자 가입 | 설정으로 열기 | Phase 3 입학 설정 전까지 닫힘 | 설정 그룹이 Phase 3에 생김 |
| admin CSP | nonce | admin만 `'unsafe-eval'` 허용 | unfold가 표준 Alpine 빌드 사용. 포털은 엄격한 nonce 유지 |
| 메일 설정 | `EMAIL_*` | `MAILERS` | Django 6.1에서 `EMAIL_*` 사용 중단 예고 |
| Python | 3.14.9 | 3.14.6 | 이 환경에서 받을 수 있는 최신 빌드 |
| mypy | 차단 | CI에서 비차단 | strict 기준 오류 75개(Django 스텁과 명령 반환값, unfold/Celery 데코레이터). Phase 13 전 정리 |
| PII 암호문 키 ID 접두 | 계획에 있음 | 없음(원본 형식 유지) | 원본 형식과 호환 우선 |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| CI 실제 실행 | 원격 저장소 연결 후 확인 | 연결 시 |
| persona 판정 규칙, SSO 로그인 흐름, 초대 | 인물·학적 모델 필요 | Phase 2 |
| 지원자 가입 화면 | 입학 설정 필요 | Phase 3 |
| 세션 종료 구현 | 세션 테이블 전체 해독(정확하나 대량 세션 시 느림) | Phase 13 부하 테스트 |
| `DJANGO_SECRET_KEY` 교체 | TOTP 비밀이 이 키로 암호화됨. 교체 절차 필요 | Phase 13 |
| Docker 이미지 | 이 환경에서 빌드 컨테이너에 네트워크가 없어 끝까지 빌드 못 함 | 연결 환경에서 |

## 6. 원본 검증 환경

원본 Laravel(PHP 8.5, intl, pdo_pgsql)을 Docker로 실행할 수 있게 해 두었다. 원본 테스트 463개 중 455개가 이 환경에서 통과한다(실패 7개는 실행 중 Gotenberg 주소 설정 문제). 원본 `setup:demo --size=small`은 90초, 행 수를 기록해 두었다(Phase 1 이후 데모 시더 비교용).
