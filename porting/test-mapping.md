# 테스트 대응표

원본 테스트 파일(`tests/`) → Django 테스트 모듈. 이식 계획 13.5절 완료 기준 7.

상태: 완료 / 부분(사유) / 예정(Phase N)

| 원본 | Django | 상태 |
|---|---|---|
| `Database/Admission/ApplicationAccessTest.php` | `tests/admission/test_application_access.py` (+ 지원자 인물의 애플리케이션 범위 `Person.visible_to` 비교) | 완료 |
| `Database/Evaluation/EvaluationAccessTest.php` | `tests/evaluation/test_evaluation_access.py` (+ 6가지 사용자에서 `EvaluationResponse.visible_to`와 RLS 비교) | 완료 |
| `Database/Foundation/DatabaseRolesTest.php` | `tests/db/test_database_roles.py` | 완료 |
| `Database/Foundation/DatabaseSessionContextTest.php` | `tests/db/test_database_session_context.py` | 완료 |
| `Database/Foundation/TimeZoneTest.php` | `tests/db/test_time_zone.py` (raw SQL + 모델 기반 사례: 업무 기간 시각, 조직 단위 날짜) | 완료 |
| `Database/Grading/FinalizedGradeGuardTest.php` | `tests/grading/test_finalized_grade_guard.py` | 완료 |
| `Database/Grading/GradeAccessTest.php` | `tests/grading/test_grade_access.py` (+ 학기 기록·성적 정정 요청의 `visible_to`와 RLS 결과 비교, 9가지 사용자) | 완료 |
| `Database/I18n/I18nFunctionTest.php` | `tests/i18n/test_i18n_function.py` (+ `zh-hans` keys, Python 일치) | 완료 |
| `Database/Offering/ScheduleConflictTest.php` | `tests/offering/test_schedule_conflict.py` | 완료 |
| `Database/Organization/OrgUnitHierarchyTest.php` | `tests/db/test_org_unit_hierarchy.py` | 완료 |
| `Database/Person/StudentRecordAccessTest.php` | `tests/person/test_student_record_access.py` (애플리케이션 범위와 RLS 결과 7가지 사용자, 범위 밖 수정 0건, 인물 RLS) | 완료 |
| `Database/Registration/ConcurrentRegistrationTest.php` | `tests/registration/test_concurrent_registration.py` (`-m concurrency`, `spawn` 프로세스 16개, 커밋된 픽스처를 끝에 삭제. 잠금을 빼면 실패함을 확인) | 완료 |
| `Database/Security/AuditTriggerTest.php` | `tests/audit/test_audit_triggers.py`, `tests/audit/test_audit_models.py` (비관리 모델 기법) | 완료 |
| `Database/Security/RowLevelSecurityTest.php` | `tests/audit/test_row_level_security.py` (원본과 같은 PoC 테이블) | 완료 |
| `Database/Term/TermConstraintsTest.php` | `tests/db/test_term_constraints.py` | 완료 |
| `Feature/Admin/AdminPagesTest.php` | `tests/admin/test_admin_panel.py` (대시보드, 한국어·중국어 화면), `tests/portal/test_portal_layout.py` (`/portal`), `tests/admin/test_reference_admin.py` (기준정보 화면 전체, 한국어·중국어), `tests/offering/test_curriculum_admin.py` (교육과정·개설강좌 화면), `tests/person/test_people_admin.py` (인물·학적·교원·학적 변동·복수전공 신청·학적/로그인 설정 화면, 한국어·중국어), `tests/registration/test_registration_admin.py` (수강신청 화면 전체, 개설강좌 수강생·대기자 탭, 포털 수강신청, 한국어), `tests/admission/test_admission_admin.py` (입학 화면·입학 설정, 한국어·중국어), `tests/grading/test_grading_admin.py` (성적 화면 전체·성적 처리 정책·포털 성적 입력·성적표, 한국어), `tests/grading/test_grading_settings.py` (성적 처리 정책 저장), `tests/attendance/test_attendance_demo.py` (포털 수강생과 출석·출석, 개설강좌 수업 회차 탭, 영어·한국어), `tests/certificate/test_certificate_admin.py` (증명서 화면 전체·증명서 설정·학적 화면 증명서 발급·포털 증명서, 한국어), `tests/evaluation/test_evaluation_demo.py`·`tests/evaluation/test_evaluation_admin.py` (강의평가 화면 전체·강의평가 설정·포털 강의평가·결과·담당 강좌 결과 열, 한국어), `tests/assessment/test_assessment_admin.py` (시험 회차·결과·정정 요청·종류 화면 전체, 회차 버튼 화면, 졸업 요건 화면, 포털 어학/종합시험, 한국어), `tests/lms/test_lms.py`·`tests/lms/test_lms_demo.py` (LMS 플랫폼·강좌 연결·동기화 기록, 다시 동기화, 한국어), `tests/graduation/test_graduation_admin.py` (졸업 요건 점검·요건 면제·저장된 점검·졸업 설정·학적 화면 졸업 버튼·보고서 7종 화면과 CSV·포털 졸업 요건, tiny 데모, 영어·한국어) | 부분(사용자·역할·감사·설정 화면 데이터셋은 각 리소스 테스트, `/portal/security`는 security 테스트) |
| `Feature/Admin/AdminPanelTest.php` | `tests/admin/test_admin_panel.py` (화면 틀), `tests/security/test_security_admin.py`, `tests/security/test_settings_pages.py` (보안·로그인 수단 설정 화면) | 부분(다른 리소스 사례는 해당 Phase) |
| `Feature/Admin/AdmissionAdminTest.php` | `tests/admission/test_admission_admin.py` (+ 지원서 화면의 검토·결정·발표·대리 응답·학적 생성 버튼, 일괄 학적 생성, 회차 목록 결과 발표, 서류 내려받기 권한, 한국어·중국어 화면) | 완료 |
| `Feature/Admin/CurriculumAdminTest.php` | `tests/offering/test_curriculum_admin.py` (화면, 강의실 충돌 안내, 시간표, 포털 개설강좌·담당 강좌·강의계획서), `tests/offering/test_section_admin.py` (권한 범위, 좌석 할당 합계, 담당 교원 탭, 다른 학기에서 복사) | 부분(복수전공·부전공 승인·신청 2개 사례는 Phase 2 인물 테스트) |
| `Feature/Admin/GradingAdminTest.php` | `tests/grading/test_grading_admin.py` (tiny 데모, 화면 전체, 확정·정정 승인, 학기 마감 미리 보기, 포털 성적 입력·성적 조회, 성적 조회 제한, 한국어 화면) | 완료 |
| `Feature/Admin/PeopleAdminTest.php` | `tests/person/test_people_admin.py` (+ 학적 등록, 인물 수정 시 신분번호 유지, 주민등록번호 보기 화면과 보안 로그) | 완료 |
| `Feature/Admin/ReferenceAdminTest.php` | `tests/admin/test_reference_admin.py` (+ 이름 다국어 검색, 세션 업무 기간 복사, CSV 가져오기 화면, 기본 성적 척도 고정, 정책) | 완료 |
| `Feature/Admin/RegistrationAdminTest.php` | `tests/registration/test_registration_admin.py` (+ 한국어 화면, 규칙 예외 취소, 지금 승격) | 완료 |
| `Feature/Admission/AdmissionJourneyTest.php` | `tests/admission/test_admission_journey.py` | 완료 |
| `Feature/Admission/AdmissionRulesTest.php` | `tests/admission/test_admission_rules.py` (+ beat 작업 `admission.expire_drafts`) | 완료 |
| `Feature/Assessment/AssessmentTest.php` | `tests/assessment/test_assessment.py` (원본 9개 사례 + 학생 접수 정원은 RLS와 관계없이 전체 접수로 계산, 회차 삭제 제한), `tests/assessment/test_assessment_access.py` (RLS와 `visible_to` 일치 8가지 사용자 × 4개 표, 학생 쓰기 차단, 결과 쓰기는 `assessments.record`만), `tests/assessment/test_assessment_admin.py` (tiny 데모의 시험 화면 전체·한국어, 목록 결과 공개, 회차 CSV 가져오기, 회차 화면 합격 점수 변경과 재판정, 외부 성적·증빙·삭제, 정정 요청과 다른 사람의 승인, 졸업 요건 화면, 포털 HTMX 접수·취소), `tests/assessment/test_assessment_seeders.py` (프로파일 멱등·관리자 수정 보존, 데모 1회·판정 규칙) | 완료 |
| `Feature/Attendance/AttendanceTest.php` | `tests/attendance/test_attendance.py` (원본 5개 사례 + 휴강 사유, 출석률 반올림, 학생 화면 집계, 명단 CSV 수식 방지, 관리 화면 수업 회차 탭), `tests/attendance/test_attendance_demo.py` (데모 시더 1회 실행, 교원·학생·관리 화면, 영어·한국어) | 완료 |
| `Feature/Certificate/CertificateTest.php` | `tests/certificate/test_certificates.py` (원본 6개 사례 + 발급번호 형식, PDF 서비스 장애, 취소 사유·권한, 진위 확인 JSON, 마스킹, 치환 항목·언어, 사진, 다시 만들기 화면, 발급 화면 오류, 실제 Gotenberg `-m gotenberg`), `tests/certificate/test_certificate_access.py` (RLS와 `visible_to` 일치 8가지 사용자, 쓰기 정책, 정책), `tests/certificate/test_certificate_admin.py` (관리·포털 화면, 설정 저장, 서식 편집, 분당 30회 제한), `tests/certificate/test_certificate_seeders.py` (프로파일 4개 언어 서식·멱등, 데모) | 완료 |
| `Feature/Curriculum/CourseTest.php` | `tests/curriculum/test_course.py` (+ `tests/curriculum/test_curriculum_admin.py`: 교과목 생성·개정·겹침 안내·졸업 요건 화면·CSV 화면) | 완료 |
| `Feature/Evaluation/EvaluationAdminTest.php` | `tests/evaluation/test_evaluation_admin.py` (Filament 동작은 관리 화면 POST, + 응답이 있는 학기의 양식 변경 거부, 강의평가 설정 저장, 표준 양식 시더 멱등, 한국어 화면) | 완료 |
| `Feature/Evaluation/EvaluationTest.php` | `tests/evaluation/test_evaluation.py` (Livewire 화면 사례는 포털 GET/POST, + 공개 전 직원 화면·의견 이스케이프, 담당 강좌 결과 열, 성적표 가림) | 완료 |
| `Feature/Grading/GpaCalculatorTest.php` | `tests/grading/test_gpa_calculator.py` | 완료 |
| `Feature/Grading/GradeWorkflowTest.php` | `tests/grading/test_grade_workflow.py` (Action을 사용자 DB 컨텍스트로 실행, + 제출 성적 직원 수정 감사) | 완료 |
| `Feature/Grading/GradingCommandsTest.php` | `tests/grading/test_grading_commands.py` | 완료 |
| `Feature/Grading/RelativeEvaluationTest.php` | `tests/grading/test_relative_evaluation.py` (Livewire 화면 사례는 포털 POST) | 완료 |
| `Feature/Grading/TermCloseTest.php` | `tests/grading/test_term_close.py` (+ chord 묶음·진행률·완료 메일, 실패 묶음) | 완료 |
| `Feature/Graduation/GraduationTest.php` | `tests/graduation/test_graduation.py` (원본 4개 사례, Action을 사용자 DB 컨텍스트로 실행, Filament·Livewire 사례는 관리 화면·포털 GET/POST, + 보안 로그 `data.exported`), `tests/graduation/test_degree_audit_support.py` (학위번호 접두어별 일련번호·토큰, 설정 형식, 복수전공·부전공 점검, 시험 합격 요건, 최신 누계 평점, 스냅샷 키), `tests/reporting/test_reporting_access.py` (reporting 뷰 8개 × 사용자 7종에서 `visible_to`와 RLS 일치, 읽기 전용, 세션 로케일), `tests/reporting/test_report_catalog.py` (열·매개변수 허용 목록, 하위 조직, 미수강 학생, CSV 형식·시각 표기, 화면·CSV 권한과 감사) | 완료 |
| `Feature/I18n/LocaleTest.php` | `tests/i18n/test_locale.py`, `tests/i18n/test_translatable_field.py`, `tests/i18n/test_formatting.py`, `tests/settings/test_institution_settings.py` | 완료 (로그인 화면 대신 테스트 뷰로 협상 확인) |
| `Feature/I18n/TranslationCommandsTest.php` | `tests/i18n/test_translation_commands.py`, `tests/i18n/test_convert_translations.py` | 완료 (gettext/xlsx로 전환) |
| `Feature/Lms/LmsTest.php` | `tests/lms/test_lms.py` (원본 4개 사례 + 인증 정보 유지·교체·데이터 감사 마스킹, 다시 동기화 성공·커넥터 오류, 수강 작업·야간 대조 작업, 3개 표 `visible_to` = RLS, 기록 상세), `tests/lms/test_lms_demo.py` (데모 LMS 시더, 한국어 LMS 화면) | 완료 |
| `Feature/Offering/SectionActionsTest.php` | `tests/offering/test_section_actions.py` (+ 분반 중복, `SectionPublished` 이벤트, 폐강 사유) | 완료 |
| `Feature/Organization/ReorganizeOrgUnitTest.php` | `tests/organization/test_reorganize_org_unit.py` | 완료 |
| `Feature/Pdf/PdfRenderingTest.php` | `tests/pdf/test_pdf_rendering.py` (respx, 실제 Gotenberg는 `gotenberg` 마커) | 완료 |
| `Feature/Person/AdditionalProgramTest.php` | `tests/person/test_additional_programs.py` | 완료 |
| `Feature/Person/PersonImportTest.php` | `tests/person/test_person_import.py` | 완료 |
| `Feature/Person/PortalTest.php` | `tests/person/test_portal.py` (내 학적·내 정보·지도 학생, RLS, 재입학자 학적 선택), `tests/portal/test_portal_layout.py` (레이아웃·메뉴), `tests/security/test_security_page.py` (학교 통합 로그인 해제) | 완료 |
| `Feature/Person/StudentRecordActionsTest.php` | `tests/person/test_student_record_actions.py` | 완료 |
| `Feature/Reference/ReferenceImportTest.php` | `tests/importing/test_reference_import.py` (+ DB 거부 행의 실패 사유, 청크 큐 처리) | 완료 |
| `Feature/Registration/EnrollmentTest.php` | `tests/registration/test_enrollment.py` (+ `test_registration_support.py`: 재수강 매개변수, 대기 만료, 유보석만 부족한 대기자, 장바구니, 강좌별 승격 잠금, 정원·평가 방식 변경 제한, CSV, 카탈로그 시더; `test_registration_access.py`: `visible_to`와 RLS 일치) | 완료 |
| `Feature/Registration/LegacyRulesTest.php` | `tests/registration/test_legacy_rules.py` | 완료 |
| `Feature/Registration/PortalRegistrationTest.php` | `tests/registration/test_portal_registration.py` (학생 RLS 아래 요청, + 시간표·HTMX 부분 응답, 요청 제한) | 완료 |
| `Feature/Registration/RegistrationCommandsTest.php` | `tests/registration/test_registration_commands.py` | 완료 |
| `Feature/Security/AuthenticationTest.php` | `tests/security/test_authentication.py` | 완료 |
| `Feature/Security/AuthorizationTest.php` | `tests/security/test_authorization.py`, `tests/security/test_security_admin.py` (사용자·역할·할당 관리 화면) | 완료 |
| `Feature/Security/EmailCodeTwoFactorTest.php` | `tests/security/test_email_code_two_factor.py`, `tests/security/test_security_page.py` (포털 보안 화면 TOTP·복구 코드) | 완료 |
| `Feature/Security/HardeningTest.php` | `tests/security/test_hardening.py`, `tests/reporting/test_report_catalog.py` (CSV 수식 사례 `test_neutralises_spreadsheet_formulas_in_csv_cells`), `tests/person/test_person_pii.py` (암호화 식별자 제외) | 완료 (같은 규칙의 명단 CSV용 `spreadsheet_cell`은 `tests/attendance/test_attendance.py`) |
| `Feature/Security/MfaPolicyTest.php` | `tests/security/test_mfa_policy.py` | 완료 |
| `Feature/Security/PersonalDataEncryptionTest.php` | `tests/pii/test_personal_data_encryption.py` (테스트 전용 모델 + 임시 테이블, 원본 암호문·해시 형식 고정), `tests/person/test_person_pii.py` (Person 암호화·검색·마스킹·재암호화), `tests/person/test_people_admin.py` (표시 해제 화면) | 완료 |
| `Feature/Security/SecurityCommandsTest.php` | `tests/security/test_security_commands.py` (+ `security_create_administrator`, `security_sync_permissions`, 역할 템플릿), `tests/person/test_person_commands.py` (`people_find_duplicates`) | 완료 |
| `Feature/Security/SignInMethodsTest.php` | `tests/security/test_sign_in_methods.py` (학번 로그인, 동일 실패 메시지, 잠금, SSO 가짜 OIDC 제공자: 로그인, audience·nonce·issuer 거부, 학교 이메일 자동 연결, SSO 뒤 2단계 인증, 연결, 졸업생 비밀번호 로그인) | 완료 |
| `Feature/Setup/ReferenceSeedersTest.php` | `tests/setup/test_reference_seeders.py` | 완료 |
| `Feature/Setup/SetupCommandsTest.php` | `tests/setup/test_setup_commands.py` (+ 시간대 거부, 성적 척도 고정, `--student-accounts` 파일), `tests/person/test_person_seeders.py` (학적 변동 유형 필수 시더 멱등, 데모 인물·포털 계정, `--student-accounts` 재학생 계정) | 완료 |
| `Feature/Term/ChangeTermStatusTest.php` | `tests/term/test_change_term_status.py` | 완료 |
| `Feature/Term/TermResolverTest.php` | `tests/term/test_term_resolver.py` (`term_inspect` 포함) | 완료 |
| `Feature/Term/TermSessionTest.php` | `tests/term/test_term_session.py` (+ 전체 대상 `{}` 저장) | 완료 |
| `Feature/Tooling/AuditCorrelationTest.php` | `tests/core/test_audit_correlation.py` (작업·명령), `tests/importing/test_import_correlation.py` (관리 화면 CSV 가져오기 작업, `reference_import`) | 완료 |
| `Feature/Tooling/AuditedCommandTest.php` | `tests/core/test_audited_command.py` (테스트 전용 명령) | 부분(`security_sync_permissions`의 dry-run·`--force` 사례는 security 테스트, `naming_check` 종료 코드 2는 naming 테스트) |
| `Feature/Tooling/CommandDocumentationTest.php` | `tests/tooling/test_command_documentation.py` (4개 언어, Django 명령, 상대 링크, 언어 간 파일 목록, `createsuperuser` 비활성) | 완료 |
| `Feature/Tooling/OperationsCommandsTest.php` | `tests/audit/test_audit_chain.py` (seal·verify·prune), `tests/media/test_media.py` (media_prune_orphans) | 부분(`system_health_check`는 Phase 13) |
| `PHPStan/NoDynamicRawSqlRuleTest.php` | `tests/tooling/test_raw_sql_check.py` (+ `tests/tooling/data/raw_sql_examples.py`) | 완료 |
| `Unit/Security/PasswordHashingTest.php` | `tests/security/test_password_hashing.py` | 완료 |
| `Unit/Targeting/TargetCriteriaTest.php` | `tests/unit/test_target_criteria.py` | 완료 |
| `Unit/Tooling/CheckNamingTest.php` | `tests/tooling/test_naming_check.py` | 완료 |

Django에만 있는 테스트

| Django | 내용 |
|---|---|
| `tests/db/test_schema_equivalence.py` | 원본 스키마 지문과 비교 (ADR 0001-django) |
| `tests/db/test_model_schema.py` | 모델 필드와 실제 열 일치 |
| `tests/api/test_api.py` | API v1(원본에 없음, Phase 12): 세션·knox 토큰 발급·사용·회수와 감사, 만료·비활성 계정, 토큰 명령, 카탈로그 권한, reporting 읽기의 RLS와 `data.exported`, throttle 3종, 스키마·Swagger UI 접근, 상태 점검, 증명서 진위 확인 JSON, LMS 콜백(동기화 결과, 점수 전달 → 초안) |
