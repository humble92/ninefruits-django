# 0002-django. 다형 참조 열에는 Django 모델 레이블(소문자)을 저장한다

- 상태: 채택 (2026-10-24, Phase 0)
- 관련: [이식 계획 1절(데이터 이관), 8절, 10절 파일](../porting-plan.md), [0001-django](0001-django-schema-from-original-ddl.md), 원본 ADR 0002

## 배경

원본에는 "어떤 모델의 몇 번 행"을 가리키는 다형 참조 열이 있다. Eloquent는 여기에 PHP 클래스 이름(`App\Models\Person\Person`)을 저장했다(원본은 `Relation::morphMap()`을 쓰지 않았다).

| 테이블 | 열 | 원본 사용처 |
|---|---|---|
| `audit.activity_log` | `subject_type`/`subject_id`, `causer_type`/`causer_id` | 업무 감사의 대상, 수행자(spatie/laravel-activitylog) |
| `audit.security_events` | `subject_type`/`subject_id` | 보안 로그의 대상 |
| `media` | `model_type`/`model_id` | 파일 소유 객체(spatie/laravel-medialibrary) |
| `notifications` | `notifiable_type`/`notifiable_id` | DB 알림 수신자 |
| `model_has_roles`, `model_has_permissions` | `model_type`/`model_id` | spatie/laravel-permission 사용자 연결(원본도 쓰지 않음, ADR 0005) |

스키마(열 이름, 타입, 인덱스)는 0001-django에 따라 그대로 두므로 값의 형식만 정하면 된다.

## 결정

1. 다형 참조 열에는 Django 모델 레이블을 소문자로 저장한다: `app_label.modelname`(`person.person`, `security.user`). 값을 만들고 읽는 곳은 `ninefruits.core.morph` 한 곳이다(`morph_type()`, `morph_of()`, `resolve()`). Django `contenttypes`의 `ContentType` 외래 키는 쓰지 않는다. 열이 문자열이고, `django_content_type` id는 설치마다 달라 `pg_dump`/`pg_restore`로 옮길 수 없기 때문이다.
2. 레이블은 모델 클래스 이름이 아니라 `Meta.label_lower`이므로 프록시 모델이 아닌 구체 모델을 넘긴다. 모델 이름을 바꾸면 저장된 값도 데이터 마이그레이션으로 바꿔야 한다.
3. 원본 클래스와 Django 모델은 아래 표처럼 대응한다. 앱 이름은 이식 계획 5.2절, 모델 이름은 원본 클래스 이름을 따른다. 원본 데이터를 `pg_restore`로 옮긴다면 복원 뒤 다음 형태의 UPDATE로 값을 바꾼다(테이블·열마다, 표의 모든 행에 대해).

   ```sql
   SELECT set_config('app.audit_maintenance', 'on', true);  -- audit.* 테이블은 같은 트랜잭션에서
   UPDATE media SET model_type = 'person.person' WHERE model_type = 'App\Models\Person\Person';
   ```

   `audit.*` 테이블의 값을 바꾸면 `row_hash`가 달라지므로 `audit_verify_chain`이 불일치를 보고한다. 감사 기록은 바꾸지 말고 원본 값 그대로 두는 것을 권장한다. 화면은 두 형식을 모두 읽는다(관리 화면의 "대상" 표시가 PHP 클래스 이름이면 마지막 부분을, Django 레이블이면 모델 이름을 보여 준다). `media_prune_orphans`는 대응하지 않는 PHP 클래스 이름을 소유자가 없는 행으로 보므로, 원본 미디어를 옮겼다면 먼저 `media.model_type`을 바꾼 뒤 실행한다.
4. 원본에서 감사 기록 테이블 모델은 이름이 바뀐다: `App\Models\Security\Activity` → `audit.activitylog`(spatie 모델 이름 대신 테이블 이름을 따른다).

## 대응표

| 원본 PHP 클래스 | Django 레이블 |
|---|---|
| `App\Models\Admission\AdmissionCycle` | `admission.admissioncycle` |
| `App\Models\Admission\AdmissionCycleDocumentType` | `admission.admissioncycledocumenttype` |
| `App\Models\Admission\AdmissionCycleProgram` | `admission.admissioncycleprogram` |
| `App\Models\Admission\Application` | `admission.application` |
| `App\Models\Assessment\AssessmentComponent` | `assessment.assessmentcomponent` |
| `App\Models\Assessment\AssessmentComponentScore` | `assessment.assessmentcomponentscore` |
| `App\Models\Assessment\AssessmentRegistration` | `assessment.assessmentregistration` |
| `App\Models\Assessment\AssessmentResult` | `assessment.assessmentresult` |
| `App\Models\Assessment\AssessmentResultCorrection` | `assessment.assessmentresultcorrection` |
| `App\Models\Assessment\AssessmentSession` | `assessment.assessmentsession` |
| `App\Models\Assessment\AssessmentType` | `assessment.assessmenttype` |
| `App\Models\Attendance\AttendanceRecord` | `attendance.attendancerecord` |
| `App\Models\Attendance\ClassMeeting` | `attendance.classmeeting` |
| `App\Models\Certificate\CertificateIssue` | `certificate.certificateissue` |
| `App\Models\Certificate\CertificateTemplate` | `certificate.certificatetemplate` |
| `App\Models\Certificate\CertificateType` | `certificate.certificatetype` |
| `App\Models\Curriculum\Course` | `curriculum.course` |
| `App\Models\Curriculum\CourseCategory` | `curriculum.coursecategory` |
| `App\Models\Curriculum\CourseEquivalency` | `curriculum.courseequivalency` |
| `App\Models\Curriculum\CourseRequisite` | `curriculum.courserequisite` |
| `App\Models\Curriculum\CourseVersion` | `curriculum.courseversion` |
| `App\Models\Curriculum\CurriculumRequirement` | `curriculum.curriculumrequirement` |
| `App\Models\Curriculum\CurriculumRequirementSet` | `curriculum.curriculumrequirementset` |
| `App\Models\Evaluation\EvaluationAnswer` | `evaluation.evaluationanswer` |
| `App\Models\Evaluation\EvaluationCompletion` | `evaluation.evaluationcompletion` |
| `App\Models\Evaluation\EvaluationForm` | `evaluation.evaluationform` |
| `App\Models\Evaluation\EvaluationQuestion` | `evaluation.evaluationquestion` |
| `App\Models\Evaluation\EvaluationResponse` | `evaluation.evaluationresponse` |
| `App\Models\Evaluation\TermEvaluation` | `evaluation.termevaluation` |
| `App\Models\Facility\Building` | `facility.building` |
| `App\Models\Facility\Room` | `facility.room` |
| `App\Models\Grading\EvaluationMethodRequest` | `grading.evaluationmethodrequest` |
| `App\Models\Grading\GradeChangeRequest` | `grading.gradechangerequest` |
| `App\Models\Grading\GradeScale` | `grading.gradescale` |
| `App\Models\Grading\GradeScaleItem` | `grading.gradescaleitem` |
| `App\Models\Grading\TermRecord` | `grading.termrecord` |
| `App\Models\Graduation\DegreeAudit` | `graduation.degreeaudit` |
| `App\Models\Graduation\DegreeRequirementWaiver` | `graduation.degreerequirementwaiver` |
| `App\Models\Institution\Country` | `institution.country` |
| `App\Models\Institution\Language` | `institution.language` |
| `App\Models\Institution\LookupType` | `institution.lookuptype` |
| `App\Models\Institution\LookupValue` | `institution.lookupvalue` |
| `App\Models\Lms\LmsCourseLink` | `lms.lmscourselink` |
| `App\Models\Lms\LmsPlatform` | `lms.lmsplatform` |
| `App\Models\Lms\LmsSyncLog` | `lms.lmssynclog` |
| `App\Models\Lms\LmsUserLink` | `lms.lmsuserlink` |
| `App\Models\Offering\Section` | `offering.section` |
| `App\Models\Offering\SectionInstructor` | `offering.sectioninstructor` |
| `App\Models\Offering\SectionMeeting` | `offering.sectionmeeting` |
| `App\Models\Offering\SectionSeatGroup` | `offering.sectionseatgroup` |
| `App\Models\Offering\Syllabus` | `offering.syllabus` |
| `App\Models\Organization\OrgUnit` | `organization.orgunit` |
| `App\Models\Organization\OrgUnitSuccession` | `organization.orgunitsuccession` |
| `App\Models\Organization\OrgUnitType` | `organization.orgunittype` |
| `App\Models\Organization\Program` | `organization.program` |
| `App\Models\Person\AccountInvitation` | `person.accountinvitation` |
| `App\Models\Person\AdditionalProgramRequest` | `person.additionalprogramrequest` |
| `App\Models\Person\AdvisorAssignment` | `person.advisorassignment` |
| `App\Models\Person\Guardian` | `person.guardian` |
| `App\Models\Person\Instructor` | `person.instructor` |
| `App\Models\Person\Person` | `person.person` |
| `App\Models\Person\StudentRecord` | `person.studentrecord` |
| `App\Models\Person\StudentRecordProgram` | `person.studentrecordprogram` |
| `App\Models\Person\StudentStatusChange` | `person.studentstatuschange` |
| `App\Models\Person\StudentStatusChangeType` | `person.studentstatuschangetype` |
| `App\Models\Registration\CartItem` | `registration.cartitem` |
| `App\Models\Registration\CreditLimitPolicy` | `registration.creditlimitpolicy` |
| `App\Models\Registration\Enrollment` | `registration.enrollment` |
| `App\Models\Registration\RegistrationAttempt` | `registration.registrationattempt` |
| `App\Models\Registration\RegistrationHold` | `registration.registrationhold` |
| `App\Models\Registration\RegistrationOverride` | `registration.registrationoverride` |
| `App\Models\Registration\RegistrationRule` | `registration.registrationrule` |
| `App\Models\Registration\RegistrationRuleSet` | `registration.registrationruleset` |
| `App\Models\Registration\WaitlistEntry` | `registration.waitlistentry` |
| `App\Models\Security\Activity` | `audit.activitylog` |
| `App\Models\Security\Permission` | `security.permission` |
| `App\Models\Security\RecordChange` | `audit.recordchange` |
| `App\Models\Security\Role` | `security.role` |
| `App\Models\Security\RoleAssignment` | `security.roleassignment` |
| `App\Models\Security\SecurityEvent` | `audit.securityevent` |
| `App\Models\Security\UserIdentity` | `security.useridentity` |
| `App\Models\Term\AcademicYear` | `term.academicyear` |
| `App\Models\Term\Term` | `term.term` |
| `App\Models\Term\TermSession` | `term.termsession` |
| `App\Models\Term\TermType` | `term.termtype` |
| `App\Models\Term\TermWindow` | `term.termwindow` |
| `App\Models\Term\TimeSlot` | `term.timeslot` |
| `App\Models\User` | `security.user` |

## 결과

- Django 쪽 코드는 `morph_type(obj)`로만 값을 만든다. 테스트(`tests/audit/test_audit_logger.py`, `tests/media/test_media.py`)가 `security.user` 형식을 고정한다.
- 위 표의 대부분은 아직 모델이 없다(Phase 1~12에서 생긴다). 모델을 만들 때 이름이 이 표와 다르면 표를 함께 고친다.
