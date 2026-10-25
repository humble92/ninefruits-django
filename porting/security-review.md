# 보안 점검 (Phase 13)

- 기준: 원본 [Phase 13 보고서](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-13-report.md) 5절(보안 점검 결과와 수정), 원본 `tests/Feature/Security/HardeningTest.php`, 이식 계획 4.1(포함: H1·H3·H4·H5·M1·M6·M7·M8·L1·L2·L4·L5)과 4.2(제외: 5.2절 후속 과제, 단 Django가 자연스럽게 해결하는 것은 받아들인다)
- 방법: 원본의 수정마다 Django 구현 위치와 테스트를 찾고, 없거나 원본이 Filament에 맡긴 부분은 테스트를 더하거나 고쳤다. 원본 `HardeningTest.php` 6건은 원본 앱에서 다시 실행해 통과를 확인했다(오라클). 이어서 Django 쪽에만 있는 구성(allauth, 프록시, `SECRET_KEY`, 세션)을 따로 점검했다.
- 결과 요약: 5.1의 12건은 모두 구현되어 있고 테스트가 있다(이번에 5건 보강). 5.2의 후속 과제 중 M5(IP 단위 로그인 제한)와 파일 다운로드 `nosniff`는 Django/allauth 기본 기능으로 해결되었고, 나머지는 원본과 같은 수준으로 남는다. Django 고유 발견 4건 중 3건을 고쳤고 1건(세션 유휴 만료)은 결정이 필요해 남겼다.

## 1. 원본 5.1 수정 항목

| 번호 | 심각도 | 원본 수정 | Django 구현 | 테스트 |
|---|---|---|---|---|
| H1 | 높음 | `Person`에 `#[Hidden]`: 암호화 칼럼과 해시를 배열·JSON(Livewire 폼 상태)에서 제외 | Django 폼은 서버 렌더링이라 폼 상태가 브라우저로 가지 않는다. 그래도 같은 원칙: `EncryptedPiiField`·`PiiHashField`는 `editable=False`(`ninefruits/pii/fields.py`)라 `ModelForm`, `model_to_dict`, 직렬화에 들어가지 않는다. 인물 수정 화면은 입력 전용 필드(`national_id_input`, `passport_number_input`, `ninefruits/person/admin/people.py`)와 마스킹 표시, 사유를 받는 표시 해제(보안 이벤트 `sensitive_data.revealed`)만 쓴다. `__repr__`·`__str__`에도 없다 | `tests/person/test_person_pii.py::test_keeps_encrypted_identifiers_out_of_repr_forms_and_serialization`, `tests/person/test_people_admin.py::test_reveals_a_national_id_once_and_records_it`, **추가** `tests/security/test_hardening.py::test_keeps_encrypted_identifiers_and_their_hashes_out_of_the_person_edit_screen`(평문, 암호문, 해시 모두 화면에 없음) |
| H3 | 높음 | `AssignRole`: 자기 할당 금지, 행위자에게 없는 권한이 든 역할 금지, 행위자 범위 밖 금지. CLI는 제외 | `ninefruits/security/actions/assign_role.py` (`enforce_actor_limits`, 범위는 조직 하위 포함). `security_create_administrator`와 데모 시더만 `enforce_actor_limits=False` | `tests/security/test_hardening.py::test_refuses_role_assignments_to_oneself_above_ones_own_permissions_or_outside_ones_scope` |
| H4 | 높음 | `UpdateUserAccount`: 이메일 변경 시 인증 초기화·세션 삭제·보안 이벤트·감사, 자기 비활성화 금지, 더 높은 권한 계정 수정 금지 | `ninefruits/security/actions/accounts.py::UpdateUserAccount` (세션은 Django 세션 저장소에서 사용자별로 삭제) | `test_hardening.py::test_resets_verification_ends_sessions_and_records_an_event_when_staff_change_an_email`, `::test_stops_staff_deactivating_themselves_or_editing_a_more_privileged_account` |
| H5 | 높음 | LMS 점수 불러오기를 `SaveGrades::canEnter`로 검사 | `ninefruits/lms/actions/pull_grades.py::PullGrades.handle(platform, section, actor)` → `SaveGrades().can_enter`. 포털 성적 입력의 `import_lms`도 같은 검사 | `tests/lms/test_lms.py::test_loads_platform_scores_into_the_grade_entry_screen_as_a_draft`(학생 403), **추가** `::test_refuses_to_load_platform_scores_for_someone_who_may_not_enter_the_grades`(입력 기간 밖 교원, 무관한 계정 거부, `grades.manage` 직원 허용) |
| M1 | 중간 | 제출된 성적을 직원이 바꾸면 감사 `grades.submitted_changed`(from/to) | `ninefruits/grading/actions/save_grades.py` | `tests/grading/test_grade_workflow.py::test_records_a_staff_change_of_a_submitted_grade_in_the_audit` |
| M6 | 중간 | CSV 수식 주입 방지(`=`, `+`, `-`, `@` 앞에 작은따옴표), 보고서와 명단 | `ninefruits/reporting/services/catalog.py::cell`, 명단 CSV `spreadsheet_cell`, 가져오기 실패 행 CSV `_csv_safe` | `tests/reporting/test_report_catalog.py::test_neutralises_spreadsheet_formulas_in_csv_cells`, `tests/attendance/test_attendance.py::test_roster_csv_neutralises_spreadsheet_formulas` |
| M7 | 중간 | 비밀번호 변경: `remember_token` 교체, 다른 기기 로그아웃, 보안 이벤트 | `ninefruits/security/actions/accounts.py::UpdateUserPassword` (현재 세션만 남기고 사용자의 다른 세션 삭제, `remember_token` 교체, `password.changed`). 비밀번호 재설정은 allauth 경로(보안 이벤트 `password.reset`)이고, Django는 비밀번호 해시가 바뀌면 그 사용자의 기존 세션을 모두 무효로 한다(세션 인증 해시) | `test_hardening.py::test_rotates_the_remember_token_ends_other_sessions_and_records_an_event_when_the_password_changes`, `::test_password_change_from_the_security_page_keeps_the_current_session`, `::test_refuses_a_password_change_with_a_wrong_current_password` |
| M8 | 중간 | `EnsureUserIsActive` 미들웨어(웹과 관리자 패널) | `ninefruits/security/middleware.py::EnsureUserIsActiveMiddleware` (전역 미들웨어라 포털·관리 화면·API 세션 모두). knox 토큰은 비활성 사용자를 거부 | `test_hardening.py::test_signs_a_deactivated_user_out_on_the_next_request`, **추가** `::test_signs_a_deactivated_administrator_out_of_the_admin_panel` |
| L1 | 낮음 | 수업 회차 생성·대기자 승격 헤더 액션에 `->authorize()` | unfold `@action(permissions=[...])`은 버튼 표시뿐 아니라 실행할 때도 `has_<name>_permission`을 다시 확인한다: `ninefruits/attendance/admin/__init__.py::has_generate_class_meetings_permission`(강좌 관리 가능), `ninefruits/registration/admin/roster.py::has_promote_waitlist_now_permission`(수강 관리 가능) | **추가** `test_hardening.py::test_refuses_meeting_generation_and_waitlist_promotion_to_staff_without_the_permission` |
| L2 | 낮음 | 출석부 PDF와 직원의 성적표 열람 감사 | `attendance.sheet_exported`(`ninefruits/attendance/views/downloads.py`), `transcript.viewed`(`ninefruits/grading/views/transcript.py`) | `tests/attendance/test_attendance.py::test_serves_the_roster_csv_and_the_attendance_sheet_to_the_instructor_and_staff_only`, `tests/grading/test_transcript.py::test_staff_open_records_they_can_see_and_the_view_is_recorded` |
| L4 | 낮음 | 취소된 증명서는 발급 권한자만 내려받기 | 정책 `download`(`ninefruits/certificate/policies.py`), `CertificateDownloadView` | `tests/certificate/test_certificates.py::test_issues_from_the_student_record_page_lists_the_ledger_and_lets_the_holder_download`, `tests/certificate/test_certificate_access.py::test_the_ledger_cannot_be_edited_or_deleted_by_policy` |
| L5 | 낮음 | 다운로드 파일 이름의 따옴표·개행 제거, CSV 업로드 `maxSize(5120)` | `ninefruits/media/services.py::header_safe_file_name`(미디어, 명단 CSV, 출석부). 시험 결과 CSV·증빙 5 MB(`ninefruits/assessment/admin/forms.py`). **고침**: 기준정보·인물 CSV 가져오기(`ImportCsvForm`)에 크기 제한이 없었다. 원본은 Livewire 임시 업로드 기본 한도(12 MB)가 막았으므로 같은 12 MB를 폼에서 검사한다(`ninefruits/institution/admin_support.py::IMPORT_MAX_SIZE`) | `tests/media/test_media.py::test_sanitizes_file_names_like_the_original`, **추가** `test_hardening.py::test_limits_the_size_of_csv_imports` |

## 2. 원본 5.2 후속 과제의 Django 재평가

| 번호 | 내용 | Django 상태 | 판단 |
|---|---|---|---|
| H2 | CSV 가져오기가 시스템 컨텍스트로 실행되어 행 단위 범위 검사 없음 | 같다. 가져오기 권한은 `has_perm(permission)`(범위 무관)으로 확인하고 행은 Celery 작업(`SystemTask`)이 시스템 컨텍스트로 쓴다(`ninefruits/importing/`) | **남음.** 기본 역할 템플릿은 이 권한을 전역으로만 준다. 범위 할당을 쓰기 전에 각 리소스의 행 처리에 행위자 범위 대조를 넣는다(원본 메모와 같음) |
| M2 | 포털 일부 화면이 정책 대신 소속 비교 | 같다(예: 성적 입력 `is_taught_by`/`is_in_scope_of`). RLS가 2차 방어 | **남음.** 정리 과제 |
| M3 | 복구 코드 사용 알림 없음 | 보안 이벤트 `mfa.recovery_code_used`는 기록되지만(`ninefruits/security/listeners.py`) 사용자 알림 메일은 없다 | **남음.** allauth 기본 기능 아님. 알림 추가 과제 |
| M4 | 공개 증명서 진위 확인의 속도 제한이 느슨 | 원본과 같은 30/분/IP(`ninefruits/certificate/views/public.py`, API는 `anon` 30/분). 프록시 뒤에서도 실제 클라이언트 주소 기준(3절 F1) | **남음.** 원본과 같은 수준 |
| M5 | 로그인 실패 잠금이 계정 단위만 | allauth `ACCOUNT_RATE_LIMITS`: `login_failed` 5/분/계정(원본 limiter), 그리고 allauth가 더하는 `login` 30/분/IP(`LOGIN_RATE_LIMIT_PER_IP`). 계정 잠금(`LoginIdentifierBackend`)은 그대로 | **해결(allauth 기본 기능, 계획 4.2).** 단 프록시 설정이 필요하다(3절 F1) |
| M9 | 세션 수명과 "모든 기기에서 로그아웃" 화면 없음 | 세션 수명은 환경 변수 `SESSION_LIFETIME_MINUTES`(기본 120분, 보안 설정 화면 아님). 비밀번호 변경은 다른 세션을 끝낸다. 기기 목록·전체 로그아웃 화면은 없다(allauth `usersessions` 미사용). 만료 방식은 3절 F3(유휴 만료로 고침) | **남음.** allauth `usersessions` 앱을 켜면 화면이 생기므로 이식 후 과제로 권한다 |
| L3 | 헤더 보안(CSP) 세분화 | Django 6 CSP 미들웨어: `default-src 'self'`, `script-src 'self' 'nonce-…'`, `frame-ancestors 'none'`, 관리 화면은 `csp_override`. `style-src`에 `'unsafe-inline'`(unfold, Alpine 인라인 스타일)이 남는다 | **부분 해결.** 스크립트는 nonce로 원본보다 엄격. 스타일 인라인 제거는 남음 |
| L6~L9 | 알림 메일의 민감 정보 최소화, 파일 다운로드의 `X-Content-Type-Options`, 데모 계정 비밀번호 정책 (원본 보고서가 번호별로 나누지 않아 주제별로 적는다) | `nosniff`: `SecurityMiddleware`(`SECURE_CONTENT_TYPE_NOSNIFF=True`)가 모든 응답에 붙인다(파일 응답 포함). 알림 메일: 원본과 같은 내용. 데모 계정: 고정 비밀번호 `demo-password`(`ninefruits/setup/conf.py`), `setup_demo`는 운영 환경에서 거부 | **`nosniff` 해결(Django 기본).** 메일과 데모 비밀번호는 남음(배포 체크리스트 메모) |

## 3. Django 고유 발견

### F1. 로그인 IP 제한과 프록시 (고침: 코디네이터)

- 내용: allauth는 원본에 없던 **IP 단위 전체 로그인 제한**(`login` 30/분/IP)을 더한다. 그런데 앱은 클라이언트 주소로 `REMOTE_ADDR`를 읽었다. Nginx 뒤에서는 모든 요청의 `REMOTE_ADDR`가 프록시 주소이므로, 학교 전체의 로그인이 분당 30회 하나의 예산을 나눠 쓰게 된다. 수강신청 첫날 아침에 로그인이 막히는 서비스 거부 상태다. `django-ratelimit`의 `key="ip"`(초대 수락, SSO, 증명서 진위 확인), API 익명 throttle, 감사의 IP 주소도 같은 문제였다.
- 수정: `ninefruits/core/http.py::client_ip`(`TRUSTED_PROXY_COUNT`개의 신뢰 프록시가 붙인 `X-Forwarded-For`의 오른쪽부터 센 주소. 왼쪽의 클라이언트가 보낸 값은 믿지 않고, 형식이 틀리거나 짧으면 `REMOTE_ADDR`), `ALLAUTH_TRUSTED_PROXY_COUNT`, `RATELIMIT_IP_META_KEY`, API throttle과 감사 미들웨어가 같은 함수를 쓴다. 제한값은 `LOGIN_RATE_LIMIT_PER_IP`(기본 `30/m/ip`, 비우면 IP 제한 없음 = 원본과 같음). 테스트 `tests/core/test_http.py`.
- 절충: 캠퍼스 무선망처럼 많은 학생이 NAT 주소 하나로 나가면 분당 30회로는 부족하다. 값을 올리면(예: `300/m/ip`) 같은 주소에서 여러 계정을 번갈아 시도하는 **크리덴셜 스터핑**을 덜 막는다(계정별 5/분 제한과 잠금은 계정마다만 작동한다). 학교 NAT 주소를 알면 프록시나 WAF에서 그 주소만 별도로 다루고 앱의 기본값은 낮게 두는 것이 낫다. 배포 체크리스트(p13-docs)가 `TRUSTED_PROXY_COUNT`, `LOGIN_RATE_LIMIT_PER_IP`를 다룬다.

### F2. `DJANGO_SECRET_KEY` 교체가 2단계 인증을 깨뜨림 (고침)

- 내용: 인증 앱 TOTP 비밀값, 복구 코드 시드, SSO 클라이언트 비밀값은 `SECRET_KEY`에서 만든 Fernet 키로 암호화된다(`ninefruits/security/crypto.py`). Django의 `SECRET_KEY_FALLBACKS`는 세션·서명·비밀번호 재설정 토큰에만 적용되므로, 키를 바꾸면 이 비밀값을 읽을 수 없어 모든 사용자의 2단계 인증을 초기화해야 했다. 설정도 `SECRET_KEY_FALLBACKS`를 읽지 않았다(키 관리 문서에 "Phase 13에서 정한다"로 남아 있었다).
- 수정: 설정이 `DJANGO_SECRET_KEY_FALLBACKS`(쉼표 목록)를 읽는다. 복호화는 현재 키와 이전 키를 차례로 시도한다(`MultiFernet`). 새 명령 `security_reencrypt_secrets`(`--dry-run`, 감사 기록)가 이전 키로 암호화된 값을 현재 키로 다시 쓴다. 기기 기억 쿠키의 HMAC도 이전 키를 받아들인다(`ninefruits/security/services/trusted_devices.py`). 절차는 `docs/manual/*/operations/security-keys.md` 4개 언어, 명령은 `commands.md` 4개 언어.
- 테스트: `tests/security/test_key_rotation.py`(이전 키로 읽기와 재암호화, 교체 중 로그인 유지와 이전 키 삭제 뒤 미사용 세션 종료, 기기 기억, 명령의 건수·감사·이전 키 없이 TOTP와 복구 코드·SSO 비밀값 동작, 읽을 수 없는 값 보고).
- 남는 것: 이메일 2단계 코드 해시는 현재 키만 쓴다(유효 10분이라 교체 직전 코드는 다시 요청). 문서에 적었다.

### F3. 세션 만료가 유휴 기준이 아님 (고침, 코디네이터)

- 내용: 원본 `SESSION_LIFETIME=120`은 마지막 요청부터 120분(유휴 만료)이다. Django는 `SESSION_SAVE_EVERY_REQUEST=False`(기본)라 세션을 바꾸지 않는 요청은 만료 시각을 늘리지 않아, **로그인 120분 뒤 일하던 중에도 로그아웃**되었다(성적 입력 중 저장 안 된 값 손실 가능).
- 선택지: `SESSION_SAVE_EVERY_REQUEST=True`는 원본과 같지만 요청마다 캐시·DB 쓰기가 생긴다. 절대 만료 유지는 쓰기가 없지만 사용자 경험이 원본보다 나쁘다.
- 결정: 중간안. `ninefruits.security.middleware.SlidingSessionExpiryMiddleware`가 로그인한 세션의 만료 시각을 최대 `SESSION_REFRESH_SECONDS`(300초)마다 한 번 늘린다. 유휴 한도는 115~120분, 쓰기는 사용자당 5분에 최대 한 번이다. 익명 세션은 늘리지 않는다. 테스트 `tests/security/test_session_expiry.py`.

### F4. 기준정보·인물 CSV 가져오기 크기 제한 없음 (고침)

1절 L5 참조. 원본은 Livewire 업로드 한도가 있었고, Django `FileField`는 한도가 없다(`DATA_UPLOAD_MAX_MEMORY_SIZE`는 파일에 적용되지 않는다).

### 그 밖에 확인한 것 (문제 없음)

- 관리 화면 로그인은 Django 기본 로그인 폼이 아니라 allauth로 보낸다(`NinefruitsAdminSite.login`). 그래서 2단계 인증, 잠금, 속도 제한을 우회하는 경로가 없다.
- 운영 설정: `DEBUG` 기본 꺼짐, HSTS, `SESSION_COOKIE_SECURE`·`CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS=DENY`, `SECURE_REFERRER_POLICY=same-origin`. `SECURE_PROXY_SSL_HEADER`는 프록시가 `X-Forwarded-Proto`를 항상 덮어쓴다는 전제다(배포 체크리스트).
- SQL: 원시 SQL은 상수 문자열과 바인딩만(`tools/checks/raw_sql.py`).

## 4. 정적 분석과 의존성

| 도구 | 결과 | 메모 |
|---|---|---|
| `uv run mypy` (strict, `ninefruits`, `config`, `tools/checks`) | 오류 0 (711개 파일) | 시작 시 675건. unfold에 `py.typed`가 없어 장식자 367건이 `untyped-decorator`였다. `typings/unfold/`에 쓰는 부분만 스텁(장식자는 함수 서명 유지, `ModelAdmin`/인라인은 Django 클래스, 대화 폼, 목록 필터)을 두고, Celery는 `celery-types`(dev 의존성)를 더했다. 나머지는 코드를 고쳤다(모델 클래스 대상 정책 검사 `policy_allows`, 로그인 사용자 `signed_in_user`, `Any`를 반환하던 곳의 타입 지정, FK 확인 방식, `on_commit`의 `partial` 등). 남은 `# type: ignore`는 이유를 단 것만: 명령 `handle()`이 종료 코드를 반환하는 설계(`StatusCommand`, 38곳), 타입 정보가 없는 라이브러리 상속(allauth·knox·import-export, 8곳), django-stubs에 없는 Django 내부(`_post_clean`, `_prefetched_objects_cache`, `base_fields`), 프록시 모델 매니저, DRF의 인스턴스 권한(`HasCatalogPermission`). CI의 mypy 단계는 이제 차단(`continue-on-error` 제거) |
| `bandit -r ninefruits -ll` | 중간 이상 0 | 시작 시 중간 3건, 모두 오탐: 상수 SQL에 값만 바인딩하는 `RawSQL` 2건(`person/models/person.py`, `person/models/student_record.py`), 상수 구분자 `mark_safe("<br>")` 1건. 이유와 함께 `# nosec B611`/`# nosec B308`. 낮음 11건: B105 9건(이벤트 이름 `password.changed` 등, 세션 키 이름, 빈 기본값, 데모 비밀번호), B101 1건(타입 좁히기용 `assert`), B311 1건(데모 시더의 난수). 모두 보안 영향 없음 |
| `pip-audit --strict` (`uv export`, 해시 포함) | 취약점 0 (패키지 164개) | |
| `ruff check`, `ruff format --check` | 통과 | |

## 5. 번역 추출 (`gettext_now`)

`gettext as gettext_now`로 가져온 문자열은 `makemessages`가 추출하지 못해 카탈로그에도, `i18n_missing`에도 나타나지 않았다(4개 파일, 7곳). 일반 `gettext`로 바꾸고 해당 앱(`registration`, `institution`) 카탈로그를 다시 추출해 원본 번역으로 채웠다(원본에 없는 2개 문구는 직접 번역). 같은 일이 다시 생기지 않도록 `tests/i18n/test_translation_aliases.py`가 `django.utils.translation`의 함수를 추출 키워드가 아닌 이름으로 가져오면 실패한다.
