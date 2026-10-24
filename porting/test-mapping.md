# 테스트 대응표

원본 테스트 파일(`tests/`) → Django 테스트 모듈. 이식 계획 13.5절 완료 기준 7.

상태: 완료 / 부분(사유) / 예정(Phase N)

| 원본 | Django | 상태 |
|---|---|---|
| `Database/Admission/ApplicationAccessTest.php` | `tests/admission/test_application_access.py` (+ 지원자 인물의 애플리케이션 범위 `Person.visible_to` 비교) | 완료 |
| `Database/Evaluation/EvaluationAccessTest.php` |  |  |
| `Database/Foundation/DatabaseRolesTest.php` | `tests/db/test_database_roles.py` | 완료 |
| `Database/Foundation/DatabaseSessionContextTest.php` | `tests/db/test_database_session_context.py` | 완료 |
| `Database/Foundation/TimeZoneTest.php` | `tests/db/test_time_zone.py` (raw SQL + 모델 기반 사례: 업무 기간 시각, 조직 단위 날짜) | 완료 |
| `Database/Grading/FinalizedGradeGuardTest.php` |  |  |
| `Database/Grading/GradeAccessTest.php` |  |  |
| `Database/I18n/I18nFunctionTest.php` | `tests/i18n/test_i18n_function.py` (+ `zh-hans` keys, Python 일치) | 완료 |
| `Database/Offering/ScheduleConflictTest.php` | `tests/offering/test_schedule_conflict.py` | 완료 |
| `Database/Organization/OrgUnitHierarchyTest.php` | `tests/db/test_org_unit_hierarchy.py` | 완료 |
| `Database/Person/StudentRecordAccessTest.php` | `tests/person/test_student_record_access.py` (애플리케이션 범위와 RLS 결과 7가지 사용자, 범위 밖 수정 0건, 인물 RLS) | 완료 |
| `Database/Registration/ConcurrentRegistrationTest.php` | `tests/registration/test_concurrent_registration.py` (`-m concurrency`, `spawn` 프로세스 16개, 커밋된 픽스처를 끝에 삭제. 잠금을 빼면 실패함을 확인) | 완료 |
| `Database/Security/AuditTriggerTest.php` | `tests/audit/test_audit_triggers.py`, `tests/audit/test_audit_models.py` (비관리 모델 기법) | 완료 |
| `Database/Security/RowLevelSecurityTest.php` | `tests/audit/test_row_level_security.py` (원본과 같은 PoC 테이블) | 완료 |
| `Database/Term/TermConstraintsTest.php` | `tests/db/test_term_constraints.py` | 완료 |
| `Feature/Admin/AdminPagesTest.php` | `tests/admin/test_admin_panel.py` (대시보드, 한국어·중국어 화면), `tests/portal/test_portal_layout.py` (`/portal`), `tests/admin/test_reference_admin.py` (기준정보 화면 전체, 한국어·중국어), `tests/offering/test_curriculum_admin.py` (교육과정·개설강좌 화면), `tests/person/test_people_admin.py` (인물·학적·교원·학적 변동·복수전공 신청·학적/로그인 설정 화면, 한국어·중국어), `tests/registration/test_registration_admin.py` (수강신청 화면 전체, 개설강좌 수강생·대기자 탭, 포털 수강신청, 한국어), `tests/admission/test_admission_admin.py` (입학 화면·입학 설정, 한국어·중국어) | 부분(사용자·역할·감사·설정 화면 데이터셋은 각 리소스 테스트, `/portal/security`는 security 테스트) |
| `Feature/Admin/AdminPanelTest.php` | `tests/admin/test_admin_panel.py` (화면 틀), `tests/security/test_security_admin.py`, `tests/security/test_settings_pages.py` (보안·로그인 수단 설정 화면) | 부분(다른 리소스 사례는 해당 Phase) |
| `Feature/Admin/AdmissionAdminTest.php` | `tests/admission/test_admission_admin.py` (+ 지원서 화면의 검토·결정·발표·대리 응답·학적 생성 버튼, 일괄 학적 생성, 회차 목록 결과 발표, 서류 내려받기 권한, 한국어·중국어 화면) | 완료 |
| `Feature/Admin/CurriculumAdminTest.php` | `tests/offering/test_curriculum_admin.py` (화면, 강의실 충돌 안내, 시간표, 포털 개설강좌·담당 강좌·강의계획서), `tests/offering/test_section_admin.py` (권한 범위, 좌석 할당 합계, 담당 교원 탭, 다른 학기에서 복사) | 부분(복수전공·부전공 승인·신청 2개 사례는 Phase 2 인물 테스트) |
| `Feature/Admin/GradingAdminTest.php` |  |  |
| `Feature/Admin/PeopleAdminTest.php` | `tests/person/test_people_admin.py` (+ 학적 등록, 인물 수정 시 신분번호 유지, 주민등록번호 보기 화면과 보안 로그) | 완료 |
| `Feature/Admin/ReferenceAdminTest.php` | `tests/admin/test_reference_admin.py` (+ 이름 다국어 검색, 세션 업무 기간 복사, CSV 가져오기 화면, 기본 성적 척도 고정, 정책) | 완료 |
| `Feature/Admin/RegistrationAdminTest.php` | `tests/registration/test_registration_admin.py` (+ 한국어 화면, 규칙 예외 취소, 지금 승격) | 완료 |
| `Feature/Admission/AdmissionJourneyTest.php` | `tests/admission/test_admission_journey.py` | 완료 |
| `Feature/Admission/AdmissionRulesTest.php` | `tests/admission/test_admission_rules.py` (+ beat 작업 `admission.expire_drafts`) | 완료 |
| `Feature/Assessment/AssessmentTest.php` |  |  |
| `Feature/Attendance/AttendanceTest.php` |  |  |
| `Feature/Certificate/CertificateTest.php` |  |  |
| `Feature/Curriculum/CourseTest.php` | `tests/curriculum/test_course.py` (+ `tests/curriculum/test_curriculum_admin.py`: 교과목 생성·개정·겹침 안내·졸업 요건 화면·CSV 화면) | 완료 |
| `Feature/Evaluation/EvaluationAdminTest.php` |  |  |
| `Feature/Evaluation/EvaluationTest.php` |  |  |
| `Feature/Grading/GpaCalculatorTest.php` |  |  |
| `Feature/Grading/GradeWorkflowTest.php` |  |  |
| `Feature/Grading/GradingCommandsTest.php` |  |  |
| `Feature/Grading/RelativeEvaluationTest.php` |  |  |
| `Feature/Grading/TermCloseTest.php` |  |  |
| `Feature/Graduation/GraduationTest.php` |  |  |
| `Feature/I18n/LocaleTest.php` | `tests/i18n/test_locale.py`, `tests/i18n/test_translatable_field.py`, `tests/i18n/test_formatting.py`, `tests/settings/test_institution_settings.py` | 완료 (로그인 화면 대신 테스트 뷰로 협상 확인) |
| `Feature/I18n/TranslationCommandsTest.php` | `tests/i18n/test_translation_commands.py`, `tests/i18n/test_convert_translations.py` | 완료 (gettext/xlsx로 전환) |
| `Feature/Lms/LmsTest.php` |  |  |
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
| `Feature/Security/HardeningTest.php` | `tests/security/test_hardening.py` | 부분(인증·권한 사례 완료. 암호화 식별자 제외는 `tests/person/test_person_pii.py`. CSV 수식 사례는 Phase 11) |
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
