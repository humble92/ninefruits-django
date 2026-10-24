# Phase 12 LMS 연동 기반과 API 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 12](porting-plan.md#phase-12-lms-연동-기반과-api-sm), [12절 LMS 연동과 API](porting-plan.md#12-lms-연동과-api), 10절 "LMS(ADR 0017)", 원본 [Phase 12 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-12-report.md), 원본 [ADR 0017](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0017-lms-integration.md), [ADR 0004-django (API 토큰)](decisions/0004-django-api-tokens.md), [LMS 연동 가이드](../docs/lms-integration-guide.md), [관리자 매뉴얼 28장](../docs/manual/ko/admin/28-lms-integration.md)

## 1. 요약

원본 Phase 12의 LMS 연동 기반을 모두 옮겼다: 플랫폼(드라이버, PII 키로 암호화한 인증 정보, 옵션), 강좌·사용자 연결, 단계별 동기화 기록, `LmsConnector` Protocol·`ConnectorRegistry`·`NullConnector`, 도메인 이벤트(강좌 공개, 수강 확정, 수강 취소, 성적 확정) → 커밋 뒤 Celery 작업, 야간 대조(beat `lms.reconcile` 02:30)와 명령 2개(`lms_sync`, `lms_reconcile`), 성적 입력 화면의 **LMS 점수 불러오기**(Phase 6이 남긴 것, 초안만), 관리 화면 3개(LMS 플랫폼, 강좌 연결과 행 **다시 동기화**, 동기화 기록), 포털 강좌 상세(Phase 4가 남긴 것)와 담당 강좌의 LMS 링크, 데모 LMS 시더, 연동 가이드(Python 커넥터 기준으로 다시 씀), 관리자 매뉴얼 28장(4개 언어), 번역. 표 4개, 제약, 감사 트리거(인증 정보는 비밀 칼럼), RLS 정책(`db/sql/policies/lms.sql`)은 Phase 0의 스키마 재생(`core/0047`)으로 이미 있고, 이 Phase는 상태 전용 마이그레이션 `lms/0001_initial`로 모델을 맞췄다.

계획 12절의 DRF API v1을 처음 열었다(원본에는 API가 없다): `/api/v1/` 라우터, 인증은 세션 + **knox 토큰**([ADR 0004-django](decisions/0004-django-api-tokens.md)), 토큰 발급·회수 감사(`api.token_issued`, `api.token_revoked`)와 명령 2개(`api_issue_token`, `api_revoke_tokens`), 카탈로그 권한 `HasCatalogPermission("lms.manage")`, drf-spectacular 스키마 `/api/schema/`(로그인 사용자)와 Swagger UI `/api/docs/`(`admin_panel.access`만, sidecar로 CSP 유지), 엔드포인트(LMS 플랫폼 조회·강좌 연결·동기화 결과 콜백·점수 전달, reporting 뷰 8개 읽기, 증명서 진위 확인 JSON, 상태 점검, 현재 사용자, 토큰), throttle 3종(`anon` 30/분, `user` 120/분, `integration` 600/분).

- 이 Phase에서 추가한 테스트 22개(`tests/lms/` 10개, `tests/api/` 12개) 통과. 원본 `LmsTest`의 4개 사례를 모두 옮기고(원본은 오라클로 실행해 4개 통과, 51 단언), 인증 정보 유지·교체·감사 마스킹, 다시 동기화와 커넥터 오류, 수강 작업·야간 대조 작업, `visible_to` = RLS, 데모·한국어 화면 사례를 더했다. API 테스트는 인증, 권한, throttle, 스키마 접근, 콜백을 다룬다. 전체 결과는 7절.
- 빈 DB에서 `setup_install --force --profile=korean-university`와 `setup_demo --size=small --seed=42 --force`(15.8초, 다른 Phase 시더 포함) 성공. 데모: null 플랫폼 `DEMO`, 이번 학기 강좌 20개 연결, 사용자 연결 3건, 동기화 기록 26건(실패 0). 원본 보고(연결 20, 사용자 연결 3, 기록 23)와 같은 수준이다. 원본 small 데모 DB의 행 수(사용자 연결 1, 기록 21)와는 데모 계정이 있는 교원·학생 수 차이만큼 다르다.

## 2. 완료 기준

원본 계획 12절 산출물

| 항목 | 결과 | 근거 |
|---|---|---|
| `lms_platforms`, `lms_course_links`, `lms_user_links`, `lms_sync_logs` | 충족 | 모델 4개(표와 정확히 일치, `test_model_schema`), unique 제약 3개는 같은 이름으로 `Meta`에 문서로 선언. 인증 정보는 `EncryptedJSONField`(PII 암호, 바뀌지 않은 값은 암호문 유지) |
| `LmsConnector`와 `NullConnector` | 충족 | `typing.Protocol` 6개 메서드, 결정적 ID, `ConnectorRegistry`(설정 `LMS_CONNECTORS`, `register`, 테스트용 `override`). 구현 없는 드라이버는 실패로 기록되고 연결이 "실패"(`test_lms.py`) |
| 도메인 이벤트 → 연동 작업 | 충족 | `SectionPublished` → `lms.sync_section`, `EnrollmentConfirmed`/`EnrollmentDropped` → `lms.sync_enrollment`(활성 플랫폼, 명단 동기화가 켜진 플랫폼만), `GradesFinalized` → 보내지 않음. `core.events.listen(..., after_commit=True)`, 작업은 `SystemTask`, 3회 재시도 |
| `lms_sync`, `lms_reconcile` | 충족 | 밀어넣기(학기·강좌, dry-run, 종료 코드 1·2), 대조(빠진 구성원 추가·남은 구성원 제거, beat 02:30) |
| 점수 초안 불러오기 | 충족 | `PullGrades` + `LmsScoreImport`. 성적 입력 화면 버튼(원본과 같은 조건: 담당 교원, 방식 변경 요청 없음, 제출 전), 점수 칸만 채우고 저장하지 않음 |
| `docs/lms-integration-guide.md` | 충족 | 원본을 옮기고 3절을 Python 커넥터(클래스, 식별자, 등록·설정, 테스트 더블)로, 4절에 API 콜백 추가 |

이식 계획 12절 API

| 항목 | 결과 | 근거 |
|---|---|---|
| `/api/v1/` 라우터 | 충족 | `ninefruits/api/urls.py`, `config/urls.py`의 `api/` |
| 인증: 세션 + 토큰(knox/DRF 결정), 발급·회수 감사 | 충족 | knox 채택([ADR 0004-django](decisions/0004-django-api-tokens.md)). 토큰 요청도 DB 세션 컨텍스트가 사용자로 설정되어 RLS가 적용된다. 발급은 세션으로만(토큰으로 토큰을 만들 수 없음), 감사는 키 접두만 |
| 권한 `HasCatalogPermission` | 충족 | `ninefruits/api/permissions.py`. LMS는 `lms.manage`, 보고는 `reports.view` |
| 스키마 `/api/schema/`, Swagger UI는 관리자만 | 충족 | 스키마는 로그인 사용자, Swagger UI는 `admin_panel.access`. `manage.py spectacular --validate --fail-on-warn` 경고 0 |
| 엔드포인트: LMS 콜백(동기화 결과, 점수 전달), reporting 읽기, 증명서 진위 확인 JSON, 상태 점검 | 충족 | 4절, 연동 가이드 4절 |
| throttle 익명·사용자·연동 | 충족 | `DEFAULT_THROTTLE_RATES` + 환경 변수, 요청마다 하나로만 계산(테스트) |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `lms_sync`, `lms_reconcile`, `api_issue_token`, `api_revoke_tokens` + `test_lms.py`, `test_api.py` |
| 2. 매뉴얼 | 관리자 매뉴얼 28장 4개 언어(원본 장 + "외부 연동 API" + "이 설치본의 화면" 절), 운영 명령 레퍼런스 4개 언어(명령 4개), 연동 가이드 |
| 3. 시더, 팩토리, 데모 | 역할 템플릿의 `lms.manage`(교무 담당)는 Phase 0에 이미 있음. 데모 `DemoLmsSeeder`(`setup/seeders/demo/lms.py`, 목록 마지막, 다시 실행하면 아무것도 하지 않음). 원본에 LMS 팩토리는 없다(테스트는 모델·Action으로 만든다) |
| 4. `setup_install`, `setup_demo --size=small` | 빈 DB에서 성공 |
| 5. 번역 | `ninefruits/lms/locale/` 67개 항목(원본 값 46개는 `convert_translations.py --fill`, 나머지 21개는 직접 번역), `ninefruits/api/locale/` 2개. 성적 입력 버튼·메시지와 포털 링크 문구는 LMS 카탈로그에 두고 성적·개설 화면에 넘겨준다(다른 앱 카탈로그 무변경). `i18n_missing --strict`에 이 두 앱 문제 없음 |
| 6. 스키마 동등성 | 통과. 상태 전용 마이그레이션 `lms/0001_initial`. 스키마 변경 없음(`knox_authtoken`은 Phase 0부터 있는 Django 쪽 표) |
| 7. 테스트 대응표 | `LmsTest` 완료, `AdminPagesTest` 행에 LMS 화면 추가, Django 전용 `tests/api/test_api.py` 행 추가 |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 모델 | `LmsPlatform`(`credential(key)`), `LmsCourseLink`, `LmsUserLink`, `LmsSyncLog`. `visible_to`: 플랫폼·기록은 `lms.manage`, 강좌 연결은 로그인 사용자, 사용자 연결은 본인(+`lms.manage`). 학생·교원·관리자 세 경우에서 RLS 결과와 같음(테스트) | `ninefruits/lms/models.py` |
| 암호화 필드 | `EncryptedJSONField`: dict ↔ `cipher().encrypt(json)`. 읽은 값을 바꾸지 않고 저장하면 암호문을 그대로 쓴다(데이터 감사에 불필요한 변경이 남지 않음). `dumpdata`에도 암호문만 | `ninefruits/lms/fields.py` |
| 열거형 | `LinkStatus`, `LmsDriver`, `SyncOperation`(+ `grades.delivered`), `SyncStatus` | `lms/enums.py` |
| 커넥터 | `LmsConnector`(Protocol, `PlatformCourse` TypedDict), `NullConnector`, `ConnectorRegistry`(`DRIVERS`, `LMS_CONNECTORS`, `register`, `override`, `is_implemented`) | `lms/connectors/` |
| Action | `SyncSection`(강좌 → 교원 → 수강생, 관리 화면에서 부르면 `lms.manage` 확인 뒤 시스템 컨텍스트), `SyncEnrollment`, `PullGrades`(성적 입력 권한 확인 뒤 시스템 컨텍스트), `ReconcilePlatform`, `SavePlatform`, `RecordPlatformCallback`(동기화 결과, 점수 전달) | `lms/actions/` |
| 서비스 | `SyncLogger`(단계는 savepoint, 실패 기록은 남김), 포털 링크(`course_links_for`, `portal_links`, 담당 강좌 **LMS** 열), 성적 입력 연결점 `LmsScoreImport` | `lms/services/` |
| 이벤트·작업 | 리스너 4개(`listeners.py`), 작업 `lms.sync_section`, `lms.sync_enrollment`(3회 재시도, 60초), `lms.reconcile`(`single_instance`) | `lms/listeners.py`, `tasks.py` |
| 정책 | `LmsPolicy`(모두 `lms.manage`, 행 동작 `resync`), `LmsSyncLogPolicy`(읽기만) | `lms/policies.py` |
| 관리 화면 | **LMS 연동 > LMS 플랫폼**(코드, 드라이버 + "아직 구현되지 않음", 언어별 이름, URL, 인증 정보 `키=값` 줄 입력·되보이지 않음·비우면 유지, 사용·명단·점수 토글, 연결 수), **강좌 연결**(플랫폼·상태·학기 필터, 과목 코드 검색, 행 **다시 동기화** 확인 화면), **동기화 기록**(플랫폼·작업·상태 필터, 상세에 payload JSON) | `lms/admin/` |
| 포털 | 강좌 상세의 "{플랫폼} 강좌 열기" 링크(`offering/views/portal.py`에 한 함수, 템플릿 3줄), 담당 강좌 **LMS** 열(`teaching.register_column`), 성적 입력 **LMS 점수 불러오기**(`grading/views/portal.py`의 동작 `import_lms`, 템플릿 버튼 1개) | `lms/services/portal.py`, `services/grades.py` |
| 명령 | `lms_sync {platform} [--term] [--section] [--dry-run]`, `lms_reconcile [platform] [--term] [--dry-run]` | `lms/management/commands/` |
| 데모 시더 | `DemoLmsSeeder`: 이번 학기 공개 강좌 20개를 `SyncSection`으로 연결(행 수가 작아 일괄 삽입 불필요, small 0.7초) | `setup/seeders/demo/lms.py` |
| API | 인증(`TokenAuthentication`: knox + DB 세션 컨텍스트), 권한(`HasCatalogPermission`, `SessionOnly`), throttle(`AnonThrottle`은 `TRUSTED_PROXY_COUNT`를 따르는 `client_ip`), 페이지(`limit`/`offset`, 최대 1,000), 토큰 Action·명령, 뷰(LMS, reporting, 시스템, 토큰), OpenAPI 토큰 스킴 | `ninefruits/api/` |
| reporting 읽기 | 8개 뷰(Phase 11의 비관리 모델 `VIEW_MODELS`)를 `visible_to` + RLS(뷰가 `security_invoker`)로 읽는다. 열 이름 그대로, 열 값 일치 필터(JSON 열 제외), 요청 언어로 번역 열. 매 요청 보안 이벤트 `data.exported`(뷰, 필터, 행 수) | `api/views/reporting.py` |
| 설정 | `REST_FRAMEWORK`(인증 순서 토큰 → 세션, 기본 페이지, throttle 클래스·환경 변수), `REST_KNOX`(90일, 자동 연장 없음), `SPECTACULAR_SETTINGS`(sidecar), `INSTALLED_APPS`에 `drf_spectacular_sidecar`(uv add) | `config/settings/base.py`, `.env.example` |
| 매뉴얼·문서 | 관리자 28장 4개 언어, 운영 명령 4개 언어, 연동 가이드, ADR 0004-django | `docs/`, `porting/decisions/` |
| 번역 | 앱 카탈로그 ko, zh_Hans, lo | `lms/locale/`, `api/locale/` |

## 4. 계획과 달라진 점

| 항목 | 계획/원본 | 실제 | 이유 |
|---|---|---|---|
| 인증 정보 암호 | 원본: Laravel `encrypted:array`(APP_KEY, AES-256-CBC) | PII 암호(`PII_ENCRYPTION_KEY`, AES-256-GCM, 원본 PII와 같은 암호문 형식) | 작업 지시. Django에는 APP_KEY가 없다. 원본 설치본의 인증 정보는 그대로 옮겨지지 않으므로 이관 시 다시 입력해야 한다. `pii_reencrypt`는 이 칼럼을 다루지 않는다(연동 가이드 3.3) |
| 인증 정보 입력 | 원본: 키/값 표(Filament `KeyValue`) | 여러 줄 `키=값` 입력, 줄 번호와 함께 형식 오류 | unfold에 키/값 위젯이 없다 |
| 다시 동기화의 커넥터 오류 | 원본: 예외가 그대로 오류 화면 | "동기화 실패: ..." 메시지, 연결은 "실패" | 연결 상태가 이미 기록되므로 화면을 깨뜨리지 않는다 |
| 관리 화면·콜백의 실행 컨텍스트 | 원본: 관리 화면 동기화는 사용자 DB 컨텍스트 | `lms.manage` 확인 뒤 시스템 컨텍스트(`SyncSection(actor=)`, 콜백) | `lms.manage`만 가진 직원은 RLS 아래 수강 행을 못 보므로 명단이 빈 채로 동기화된다. 원본의 `PullGrades`와 같은 방식으로 맞췄다 |
| 점수 전달(push) | 원본: 끌어오기(`finalScores`)만 | API로 받은 점수를 `grades.delivered` 기록에 두고, 커넥터 점수가 없으면 `PullGrades`가 최근 전달분을 쓴다 | 계획 12절 "점수 전달" 콜백. 원칙(초안만, 저장 없음)은 같다 |
| 동기화 결과 콜백 | 원본에 없음 | 대기 중인 기록을 마치거나 새 기록. 강좌 결과는 연결 상태 갱신 | 계획 12절 |
| 성적 입력 버튼 위치 | 원본: 평가 방식 안내 상자 안 | 표 아래 버튼 줄(같은 표시 조건). 누르면 입력 중인 값을 지키며 점수 칸만 바꾼 화면을 다시 그린다 | Livewire 상태 대신 한 폼(Phase 6 방식). 버튼이 폼 안에 있어야 입력 값이 유지된다 |
| 담당 강좌의 LMS 링크 | 원본: 강좌 이름 옆 작은 링크 | **LMS** 열(`teaching.register_column`) | Phase 4가 만든 확장 방식 |
| 관리 화면 개설강좌의 LMS 링크 | 작업 지시: "section page" | 포털 강좌 상세에 구현(Phase 4 보고의 "강좌 상세의 LMS 링크") | 원본 관리 화면 개설강좌에는 LMS 링크가 없다. 관리 화면은 **강좌 연결**(학기 필터, 과목 코드 검색)로 본다 |
| API 명령 | 계획: 명령 2개(`lms_*`) | + `api_issue_token`, `api_revoke_tokens` | 토큰 발급·회수를 감사 기록과 함께 운영자가 하려면 필요(ADR 0004-django). 토큰 관리 화면은 만들지 않았다 |
| 상태 점검 | 계획: "상태 점검" 엔드포인트 | DB·캐시·스케줄러 심장박동만, 익명에게는 상태만 | `system_health_check` 명령(키·역할·RLS 등 전체 점검)은 Phase 13 |
| 동기화 작업 실패 시 테스트 | 원본: 동기 큐 | Celery eager에서는 예외를 그대로, 워커에서는 `retry`(60초, 3회) | 테스트에서 원인이 보이게 |
| 데모 플랫폼 이름 | 원본: en, ko, zh_CN | + lo | 지원 언어 4개 |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| 실제 커넥터 | Moodle, Open edX(가이드 5절의 함수 목록은 대상 버전에서 검증 필요), LTI 1.3, IdP, OneRoster 내보내기 | 요청 시 |
| 인증 정보 키 교체 | `pii_reencrypt`가 `lms_platforms.credentials`를 다시 암호화하지 않는다. 이전 키를 지우기 전에 인증 정보를 다시 입력해야 한다(가이드에 적음). `pii_reencrypt` 확장 검토 | Phase 13 |
| 토큰 관리 화면 | 관리 화면에서 토큰 목록·회수·발급(현재 명령·API) | 요청 시 |
| `system_health_check` | API 상태 점검과 같은 판정 기준을 명령에서 재사용 | Phase 13 |
| 플랫폼 옵션 입력 | `options`(역할 매핑)에 화면이 없다. 원본도 같음 | 커넥터 구현 시 |
| reporting API 응답량 | 페이지 최대 1,000행, 매 요청 `data.exported` 기록. BI가 큰 표를 자주 읽으면 보안 로그가 늘어난다. 대량은 `app_reporting` 역할로 DB 직접 읽기를 권장 | 운영 안내 |
| 다른 Phase 영역 | 전체 실행 중 `tests/tooling/test_command_documentation.py::test_relative_links_in_the_manuals_resolve` 실패: `docs/manual/*/README.md`의 `../../README.md`(다른 작업이 수정 중인 README 파일, 이 Phase와 무관) | 해당 작업 |

## 6. 실행 방법

`uv run manage.py setup_demo --size=small --force` 후(비밀번호 `demo-password`):

| 계정 | 볼 것 |
|---|---|
| `academic-affairs@demo.test` | 관리 화면 **LMS 연동 > LMS 플랫폼**(`DEMO`), **강좌 연결**(20개, 행 **다시 동기화**), **동기화 기록** |
| `instructor@demo.test` | 포털 **담당 강좌**의 **LMS** 열, 강좌 상세의 "시연용 LMS 강좌 열기" |
| `student@demo.test` | 연결된 강좌의 강좌 상세 링크 |

명령과 API 예:

```bash
uv run manage.py lms_sync DEMO --dry-run
uv run manage.py lms_reconcile DEMO
uv run manage.py api_issue_token academic-affairs@demo.test --days=7 --reason=시험
curl -H "Authorization: Token <토큰>" http://localhost:8000/api/v1/lms/platforms/DEMO/course-links/
curl http://localhost:8000/api/v1/health/
```

## 7. 검증 결과

| 항목 | 결과 |
|---|---|
| 이 Phase 테스트(`tests/lms/`, `tests/api/`) | 22개 통과 |
| 원본 오라클(`tests/Feature/Lms/LmsTest.php`, DB `testing_p12`) | 4개 통과(51 단언) |
| 스키마(`tests/db/`) | 통과 |
| 전체 테스트(`pytest -n 4 -m "not concurrency"`) | 1,065개 중 1,064개 통과, 1개 실패(5절 "다른 Phase 영역", 이 Phase와 무관) (142초) |
| 정적 검사 | ruff format/check, `tools/checks/raw_sql.py`, `manage.py check`, `naming_check`, `spectacular --validate --fail-on-warn` 통과. `makemigrations --check --dry-run` 변경 없음. mypy는 비차단(명령 `handle` 반환형, unfold 데코레이터, `has_perm(모델 클래스)` 등 다른 앱과 같은 종류) |
| 번역 | `i18n_missing --strict`에 `lms`, `api` 카탈로그 누락 0(남은 누락은 Phase 11 작업 중인 카탈로그) |
| 데모 | 1절 |
