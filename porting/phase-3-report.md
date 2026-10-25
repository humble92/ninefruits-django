# Phase 3 입학 지원 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 3](porting-plan.md#phase-3-입학-지원-m), 원본 [Phase 3 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-3-report.md), 원본 [ADR 0008](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0008-admissions.md)

## 1. 요약

Phase 3 작업 항목을 모두 구현했다. 지원자 가입(이메일 인증), 모집 회차(상시 접수 포함)·모집 프로그램·제출 서류, 지원서와 서류 업로드(Media), 수험 번호(회차별 원자적 일련번호), 상태 전이, 결정과 발표 분리, 등록 의사, 학생 전환(`MatriculateApplicant`, 시스템 컨텍스트), 재입학, 초안 만료(beat 작업과 명령), 공개 모집 안내 페이지, 알림 메일 2종, 입학 설정, 지원자 persona, 관리 화면, 포털 화면 2개, 데모 입학 데이터, 관리자 매뉴얼 16장(4개 언어)을 옮겼다.

- 이 Phase에서 추가한 테스트 28개(파라미터 포함 36건, `tests/admission/`) 통과. 전체 699건 중 695건 통과, 실패 4건은 같은 시각에 작업 중인 Phase 5(p5) 명령 4개가 아직 운영 매뉴얼에 없어서다(`test_command_documentation`, p5 몫).
- ruff format/check, raw SQL 검사, `manage.py check`, `makemigrations --check`, 스키마 동등성·모델 열 일치 검사 통과. `i18n_missing --strict`에서 이 Phase 카탈로그(`ninefruits/admission/locale/`, 전역 카탈로그의 가입·로그인 화면 문구) 누락 0건(남은 항목은 p5의 수강신청 문구).
- 빈 DB에서 `setup_install --force --profile=korean-university`, `setup_demo --size=small --seed=42` 성공(합계 15초). 데모 행 수는 원본 small 데모와 같다(회차 2, 모집 프로그램 7, 제출 서류 3, 지원서 32). 데모 데이터에 `admission_matriculate DEMO-2027-REG --term=2027-SP`를 실제 실행해 등록 확정자 4명의 학적이 생성됨을 확인했다(원본 보고와 같은 결과). `--size=large`는 전체 24초(지원서 6,002건, 일괄 삽입).

## 2. 완료 기준

| 완료 기준 | 결과 | 근거 |
|---|---|---|
| 지원부터 첫 수강신청까지 같은 계정으로 끊김 없이 진행 | 충족 | `tests/admission/test_admission_journey.py`: `/accounts/signup/` 가입 → 확인 메일 링크로 이메일 확인(확인 전에는 지원 화면이 확인 안내로 이동) → 포털에서 지원서 작성·서류 업로드·제출(수험 번호 `2027-REG-00001`, 접수 메일, 지원자 persona) → 합격 결정(발표 전 지원자에게는 검토 중, 메일 없음) → 관리 화면 **결과 발표**(메일, 응답 기한) → 포털에서 등록 확정 → 학적 생성(입학 학기, 입학일 = 학기 첫날, 업무 감사의 처리자 = 입학 담당) → 같은 계정이 학생 persona(지원자 아님), 같은 이메일·비밀번호로 로그인해 내 학적에서 학번 확인 → 신입생 대상 수강신청 기간에 `TermResolver`가 그 학기를 반환 |
| 재입학 시 이전 학적 보존 | 충족 | 같은 파일: 졸업생이 기존 계정으로 지원(신원 정보는 학적 값 유지) → 학적 2개(이전 학적은 졸업 상태 그대로), 계정 1개 |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `admission_matriculate`, `admission_expire_drafts` + beat 작업 `admission.expire_drafts`(03:10) + 테스트 |
| 2. 매뉴얼 | 운영 명령 레퍼런스 4개 언어, 관리자 매뉴얼 16장 4개 언어(원본 장을 Django 화면·명령으로) |
| 3. 시더, 팩토리, 데모 | 필수 시더 변경 없음(코드 목록 `admission_type`, `application_document_type`과 한국 대학 프로파일의 입학 구분·제출 서류는 Phase 1에서 이미 이식). 팩토리 2개(`AdmissionCycleFactory`, `ApplicationFactory` 상태 trait), 데모 `DemoAdmissionSeeder`(일괄 삽입, `--seed` 재현, 멱등, 데모 계정 2개) + 테스트 |
| 4. `setup_install`, `setup_demo --size=small` | 빈 DB에서 성공 |
| 5. 번역 | 앱 카탈로그 `ninefruits/admission/locale/` 신설, `convert_translations.py --fill`로 원본 값 채움(156건). 원본에 없는 문구 11개는 직접 번역. 가입·로그인 화면 문구는 전역 카탈로그에 원본 키로 추가 |
| 6. 스키마 동등성 | 통과(도메인 마이그레이션은 상태 전용 `admission/0001_initial`) |
| 7. 테스트 대응표 | 원본 4개 파일 완료로 갱신, `AdminPagesTest` 행에 입학 화면 추가 |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 모델 | `AdmissionCycle`(`accepting_applications`, `is_rolling`), `AdmissionCycleProgram`, `AdmissionCycleDocumentType`, `Application`(`visible_to`, `applicant_status`, `is_decision_changeable`, 서류 Media 컬렉션 `documents`), `ApplicationNumberSequence`. 열거형 `ApplicationStatus`(8개 상태) | `ninefruits/admission/models.py`, `enums.py` |
| 업무 Action | 원본 12개: `RegisterApplicant`, `StartApplication`, `UpdateApplication`, `UpdateApplicantPersonalDetails`, `AttachApplicationDocument`, `SubmitApplication`, `WithdrawApplication`, `DecideApplication`(검토 시작·합격·불합격), `ReleaseDecisions`, `RespondToOffer`, `MatriculateApplicant`, `ExpireDraftApplications`. 감사 이벤트 이름 원본과 같음 | `admission/actions/` |
| 수험 번호 | 원본과 같은 단일 upsert(`ON CONFLICT DO UPDATE ... RETURNING`), `{회차 코드}-{00001}` | `actions/applications.py` |
| 시스템 컨텍스트 | 가입(`system:registration`), 학적 생성(`system:matriculation`). `app.user_id`는 유지되어 데이터 변경 기록에 담당자가 남는다(ADR 0008 표 그대로) | `actions/registration.py`, `actions/matriculation.py` |
| 서류 업로드 | MIME은 내용으로 판정(PDF, JPEG, PNG), 크기는 설정 `max_document_size_mb`, 같은 종류는 교체, 형식 오류는 검증 메시지. 내려받기는 권한 확인 뷰 `/applications/<id>/documents/<media>/`(지원자 본인, 범위 안의 담당자) | `actions/applications.py`, `views/public.py` |
| 권한, RLS | 정책 2종(`AdmissionCyclePolicy`, `ApplicationPolicy`), `visible_to`가 RLS와 같은 결과(`test_application_access.py`: 5가지 사용자, 두 계층 독립 비교, 지원자의 SQL 직접 합격 처리 거부). 인물 가시성 확장 `PERSON_VISIBILITY`(볼 수 있는 지원서의 지원자) | `policies.py`, `personas.py` |
| persona | `ApplicantPersonaDetector`(진행 중이고 학적이 없는 지원서). p2가 남긴 `register_detector` 사용 | `personas.py` |
| 가입 | allauth 가입 화면을 지원자 가입으로: `ACCOUNT_FORMS["signup"]` = `ApplicantSignupForm`(성·이름·이메일·비밀번호, 저장은 `RegisterApplicant`), 확인 메일은 allauth. 설정이 꺼지면 가입 화면 404(원본과 같음). 로그인 화면에 **모집 안내 보기** 링크 | `forms.py`, `security/adapters.py`, `templates/account/signup.html`, `login.html` |
| 이메일 확인 요구 | 지원 화면은 이메일 확인 전이면 `/admissions/verify-email/`(링크 다시 보내기)로 보낸다. 다른 화면은 영향 없음(원본 `verified` 미들웨어 범위와 같음) | `views/portal.py`, `views/public.py` |
| 알림 | 접수 확인, 결과 안내 메일(커밋 뒤 발송, 수신자 언어). 계정이 없는 인물은 연락용 이메일로. 원본도 메일만 있어 DB 알림은 없음 | `notifications.py` |
| 설정 | `admissions` 그룹(가입 허용, 작성 중 지원서 만료 일수, 서류 최대 크기), 데이터 마이그레이션 `appsettings/0009_p3_admission_settings`, 관리 화면 **설정 > 입학** | `settings.py`, `settings_pages.py` |
| 스케줄 | Celery 작업 `admission.expire_drafts`(beat 항목은 Phase 0에 있음)가 `admission_expire_drafts` 명령을 실행해 원본 스케줄러처럼 명령 감사가 남는다. `single_instance` 잠금 | `tasks.py` |
| 명령 | `admission_matriculate`(AuditedCommand, `--term`·`--actor` 필수, `--dry-run`, 지원자별 트랜잭션, 실패 시 종료 코드 2), `admission_expire_drafts`(`--dry-run`) | `management/commands/` |
| 관리 화면 | 모집 회차(모집 프로그램·제출 서류 인라인 탭, 지원서 수, 행 메뉴와 회차 화면의 **결과 발표**, 사용 중 삭제 안내), 지원서(작성 중 제외, 회차·상태 필터, 수험 번호·이름 검색, 상세: 지원 내용·지원자·이전 학적·서류 링크·결정, 버튼: 검토 시작·합격·불합격(의견 필수)·결과 발표·학적 생성(입학 학기)·등록 의사 대리 입력(사유), 일괄 작업: 결과 발표·학적 생성(입학 학기 선택 화면)) | `admission/admin/` |
| 포털 | **입학 지원**(내 지원서 목록, 새 지원서: 회차를 고르면 HTMX로 프로그램 갱신, 자바스크립트 없이도 회차별 묶음으로 선택 가능), 지원서 화면(작성 중: 인적 사항·지원 내용·서류 한 화면 저장/제출, 제출 확인 대화상자, 이후: 상태·발표된 결과·등록 의사·지원 포기·학번 안내). 메뉴는 지원자 persona 또는 접수 중인 회차가 있을 때 | `views/portal.py`, `templates/admission/portal/` |
| 공개 페이지 | `/admissions/` 접수 중인 회차와 모집 프로그램, 계정 만들기/로그인 | `views/public.py`, `templates/admission/public/` |
| 데모 | `DemoAdmissionSeeder`: 정시(다음 해)·상시 회차, 상태별 지원서 30×규모 + 계정 2개(`applicant@`, `admitted@`). 인물·지원서 `bulk_create`, 수험 번호는 회차 일련번호를 실제로 진행 | `setup/seeders/demo/admission.py` |
| 매뉴얼 | 관리자 16장 4개 언어(가입 주소, 일괄 작업 사용법, 회차 행 메뉴, `uv run manage.py admission_matriculate`), 명령 레퍼런스 4개 언어 | `docs/manual/*/` |

## 4. 계획과 달라진 점

| 항목 | 원본/계획 | 실제 | 이유 |
|---|---|---|---|
| 가입 주소 | 원본 `/register` | `/accounts/signup/`(allauth) | 계획 7.1절: allauth `is_open_for_signup` + `RegisterApplicant` |
| 가입 화면의 이메일 중복 | 원본: "이미 사용 중" 오류 | allauth 계정 열거 방지 그대로(같은 이메일이면 기존 계정 안내 메일, 화면은 동일) | Phase 0 보안 설정(`ACCOUNT_PREVENT_ENUMERATION`)을 바꾸지 않았다. `RegisterApplicant`를 직접 부르면 원본처럼 오류 |
| 가입이 꺼졌을 때 POST | 원본: 검증 오류(email) | 404 | allauth는 가입 화면 전체를 닫는다. 계정이 만들어지지 않는 결과는 같음 |
| 비밀번호 규칙 | Fortify `Password::default()` | Phase 0의 Django 검사기(12자 이상 등) | 전체 계정 공통 규칙 |
| 서류 업로드 | 원본: 파일을 고르는 즉시 업로드(Livewire) | 저장/제출 때 함께 업로드(같은 폼) | 서버 렌더링. 결과는 같다(종류별 교체, 같은 검증) |
| 제출 확인 | `wire:confirm` | HTMX `hx-confirm`(자바스크립트가 없으면 확인 없이 제출) | CSP 아래 인라인 스크립트 없음 |
| 지원서 메뉴 배지 | 원본: 결정 대기 수 | 없음, 상태 필터와 제출 순 정렬로 대신 | 관리 메뉴에 배지 기반이 없다(p2 보고와 같음). 매뉴얼에 반영 |
| 상태 필터 | 원본: 작성 중 제외한 상태만 | 모든 상태(작성 중을 골라도 목록은 비어 있음) | unfold 선택 필터는 필드 선택지를 그대로 쓴다 |
| 데모 수험 번호 | 원본: 높은 범위의 임의 번호(`9####`), 일련번호 테이블 0행 | 회차 일련번호를 실제로 진행(테이블 2행) | 데모에서 새로 제출한 지원서가 기존 번호와 겹치지 않고 이어지게 |
| 접수·결과 메일 | 원본: 큐 알림 | 트랜잭션 커밋 뒤 바로 발송(평문) | Phase 0·2 메일과 같은 방식 |
| 지원자 표시 이름 | — | `User.display_name()`이 RLS로 인물을 못 읽으면 이메일로 | 가입 중 확인 메일을 만들 때 요청 컨텍스트가 아직 익명이라 인물을 읽지 못해 오류가 났다(이 Phase에서 발견해 수정) |
| 인물 병합의 지원서 이동 | p2: SQL 하위 질의 | 그대로 둠 | p2 파일. 결과가 같고 `test_admission_rules.py`의 병합 사례가 통과 |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| 수강신청(첫 수강신청 실제 수행) | 이 Phase는 `TermResolver`가 신입생 학기를 반환하는 데까지 | Phase 5 |
| 지원서 메뉴 배지 | 관리 메뉴 배지 기반이 생기면 결정 대기 수 | 필요 시 |
| 이전 학적 성적의 학점 인정, 회차별 지원서 항목, 전형료, 면접 일정 | 원본 보고의 남은 일과 같음 | 수요 확인 후 |
| 지원 통계 reporting 뷰 | 원본과 같음 | Phase 11 |
| 다른 작업자 | p5의 명령 4개(`registration_preflight` 등) 운영 매뉴얼 항목 없음, 수강신청 문구 번역 누락(전역 카탈로그) | p5 |
| 관리 화면 캡처 | 매뉴얼 화면 캡처 | Phase 13 |

## 6. 실행 방법

`uv run manage.py setup_demo --size=small` 후 데모 계정(비밀번호 `demo-password`):

| 계정 | 내용 |
|---|---|
| `applicant@demo.test` | 제출한 지원서, 결과 대기 |
| `admitted@demo.test` | 합격 발표됨. 포털 **입학 지원**에서 등록 의사 응답 가능 |
| `admissions-officer@demo.test` | 입학 담당. 관리 화면 **입학** 메뉴 |

새 지원자 흐름은 `/admissions/`에서 계정을 만들어 시험한다(메일은 Mailpit `http://localhost:8025`).
