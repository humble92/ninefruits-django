# Phase 11 졸업과 보고서 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 11](porting-plan.md#phase-11-졸업과-보고서-m), 10절 "졸업(ADR 0016)", 11절(CSV 수식 주입 방지, 정렬·필터 허용 목록, 대량 내보내기 감사), 원본 [Phase 11 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-11-report.md), 원본 [ADR 0016](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0016-graduation-and-reporting.md), [관리자 매뉴얼 26장](../docs/manual/ko/admin/26-graduation.md)·[27장](../docs/manual/ko/admin/27-reports.md)

## 1. 요약

원본의 졸업 사정과 보고서를 그대로 옮겼다. 교육과정 연도별 졸업 요건 세트에 대한 **요건 판정**(`DegreeAudit` 서비스: 교과 구분 하위 포함, 수강 학기 기준 대체과목, 지정 과목 선택, 시험 합격(`AssessmentPassCheck`), 총 학점, 최저 누계 평점, 승인된 면제), 점검 **스냅샷** 저장(`degree_audits`, 요건별 결과 jsonb, 개별·일괄·명령), 요청자≠승인자 **요건 면제**(요청·승인·반려·해제), 저장된 최신 주전공 점검이 충족일 때만 하는 **졸업 처리**(학적 변동 `graduation` + 설정 형식의 학위번호, 접두어별 원자적 일련번호), `reporting` 스키마 **뷰 8개의 비관리 모델**, **표준 보고서 7종**(화면 500행 + CSV, 수식 주입 방지, 열·매개변수 허용 목록, 감사 `reports.exported` + 보안 로그 `data.exported`), 졸업 설정 그룹과 설정 화면, 명령 `degree_audit_run`, 관리 화면(졸업 요건 점검, 요건 면제, 보고서, 학적 화면의 **졸업 요건 점검**·**요건 면제** 버튼), 포털 **졸업 요건**, 데모 졸업 시더, 관리자 매뉴얼 26·27장(4개 언어), 운영 명령 레퍼런스, 번역(앱 카탈로그 2개, 144개 항목)을 구현했다.

- reporting 비관리 모델(`ninefruits/reporting/models.py`)은 Phase 12(API)가 가져다 쓰도록 맨 먼저 만들었다(`VIEW_MODELS`로 뷰 이름 → 모델).
- 이 Phase에서 추가한 테스트 79개(`tests/graduation/` 12개, `tests/reporting/` 67개) 통과. 원본 `GraduationTest`의 4개 사례를 모두 옮겼고(원본도 오라클로 실행해 4개 통과 확인), `HardeningTest`에 남아 있던 CSV 수식 사례를 옮겼다. 전체 결과는 7절.
- 빈 DB에서 `setup_install --force --profile=korean-university`와 `setup_demo --size=small --seed=42 --force`(전체 17~22초) 성공. 데모: 이번 학기 3·4학년 점검 30건(충족 3), 승인된 면제 3건, 졸업생 1명(학위번호 `B-KOR-2026-00001`, 원본 small 데모와 같은 학생·번호), 졸업 사정용 이수 기록 120건(원본 121건). 원본 small(점검 33건, 충족 3, 면제 3)과 같은 수준이며, 점검 수 차이는 Phase 2 데모 인물(3학년 이상 재학생 29명 대 31명, 원본에만 부전공 1건)에서 온다.

## 2. 완료 기준

계획서 Phase 11 항목

| 항목 | 결과 | 근거 |
|---|---|---|
| 요건 판정 | 충족 | `DegreeAudit.evaluate/evaluate_all`: 교육과정 연도의 요건 세트, 하위 교과 구분, 수강 학기 시작일 기준 대체과목(`CourseHistory.accepted_course_ids`), 지정 과목, 시험 합격, 총 학점, 최저 누계 평점(주전공만), 같은 인물의 다른 학적 이수 인정, 승인된 면제(`test_judges_categories_...`, `test_judges_the_examination_requirement_...`) |
| 점검 스냅샷 | 충족 | `RunDegreeAudits.for_record/for_all`: 프로그램마다 한 행, `result`는 원본과 같은 키의 jsonb(`DegreeAuditResult.to_dict`), 최신 = 학생·이수 구분별 최대 id(`newest_per_student`, reporting 뷰와 같은 규칙) |
| 요건 면제(2인) | 충족 | `WaiveRequirement`: 요청(사유 필수, 열린 면제 하나: 부분 unique 위반 → 메시지), 승인·반려(자기 요청 거부, 반려 의견 필수), 해제(승인된 것만, 사유 필수), 단계마다 감사 |
| 졸업 처리·학위번호 | 충족 | `GraduateStudents.handle/batch`: 재학·최신 주전공 점검 충족 확인 → `RecordStatusChange`(유형 `graduation`) → `DegreeNumberGenerator`(`{PROGRAM}-{YYYY}-{SEQ:5}`, `INSERT ... ON CONFLICT ... RETURNING`) → 감사 `graduation.processed`. 일괄은 학생별 트랜잭션과 오류 목록 |
| reporting 뷰 8개(비관리 모델) | 충족 | `ReportStudent` 등 8개, `db_table = 'reporting"."students'`, `managed = False`, 읽기 전용(`save`/`delete` 거부), 번역 칼럼은 세션 로케일(`test_translated_columns_follow_the_session_locale`) |
| 표준 보고서 7종·CSV | 충족 | `ReportCatalog`(원본 정의 그대로: 뷰, 매개변수, 열, 정렬), UTF-8 BOM CSV, `cell()`의 수식 방지(`=`, `+`, `-`, `@`, 탭, CR), 화면 500행·CSV 100,000행 |
| 보고서 화면 | 충족 | **보고서 > 보고서**(`/admin/reports/`, `reports.view`) |
| 졸업 설정 | 충족 | 설정 그룹 `graduation`(`appsettings.0015_p11_graduation_settings`, `0016_p11_graduation_defaults`가 원본 설정 마이그레이션 2개를 그대로), **설정 > 졸업 설정**(`graduation.process`, 형식 정규식, 평점 0~5) |
| RLS와 `visible_to` | 충족 | 점검·면제: 볼 수 있는 학적(`test_shows_audits_...`). reporting 뷰 8개 × 사용자 7종에서 `visible_to`와 RLS 결과 일치(`test_reporting_access.py`, 56개 조합) |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `degree_audit_run`(`--term`, `--student-number`, `--min-year-level`, 종료 코드 1: 없는 학기) + `test_stores_audits_...` |
| 2. 매뉴얼 | 관리자 매뉴얼 26·27장 4개 언어(원본 장 + "이 설치본의 화면" 절), 운영 명령 레퍼런스 4개 언어 |
| 3. 시더, 팩토리, 데모 | 데모 `DemoGraduationSeeder`(이수 기록 일괄 삽입, 다시 실행하면 아무것도 하지 않음: `test_seeds_audits_once`). 원본에 졸업 필수 시더·팩토리는 없다(권한·역할 템플릿은 Phase 0, 학적 변동 유형 `graduation`은 Phase 2 필수 시더) |
| 4. `setup_install`, `setup_demo --size=small` | 빈 DB에서 성공 |
| 5. 번역 | `ninefruits/graduation/locale/` 75개, `ninefruits/reporting/locale/` 69개 항목, `convert_translations.py --fill`로 원본 값 채움(원본 그룹 `graduation`, `grading`, `people` 등). 원본에 없는 reporting 모델 이름 5개는 직접 번역. 이 두 앱은 `i18n_missing --strict`에 문제 없음 |
| 6. 스키마 동등성 | 통과. 상태 전용 마이그레이션 `graduation/0001_initial`, `reporting/0001_initial`(비관리). 스키마 변경 없음 |
| 7. 테스트 대응표 | `GraduationTest` 완료, `HardeningTest` 완료(CSV 수식 사례), `AdminPagesTest` 행에 이 Phase 화면 추가(원본 `AdminPagesTest`에는 졸업·보고서 데이터셋이 없어 화면 렌더링은 `test_graduation_admin.py`가 맡음) |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 모델 | `DegreeAudit`, `DegreeRequirementWaiver`(열 이름 `curriculum_requirement_set_id`, `curriculum_requirement_id`는 `db_column`), `DegreeNumberSequence` | `ninefruits/graduation/models.py` |
| reporting 모델 | `ReportStudent`, `ReportHeadcount`, `ReportTermRecord`, `ReportCourseGrade`, `ReportSectionEnrollment`, `ReportSectionMeeting`, `ReportStatusChange`, `ReportDegreeAudit`, `VIEW_MODELS`. 뷰 칼럼은 모두 nullable이라 필드도 `null=True`, 행 뒤의 학적·인물·과정·조직은 제약 없는 외래 키로 이어 둠 | `ninefruits/reporting/models.py` |
| 범위 조회 | 점검·면제: `StudentRecord.visible_to`의 학적. 뷰: 학적 단위 뷰(students, term_records, status_changes, degree_audits)는 볼 수 있는 학적, course_grades는 볼 수 있는 수강이면서 학적, headcount는 볼 수 있는 학적이 하나라도 있는 묶음(`Exists`), section_enrollments·section_meetings는 전부(아래 4절) | 같은 곳, `tests/reporting/test_reporting_access.py` |
| 열거형·데이터 | `WaiverStatus`, `DegreeAuditResult`/`RequirementResult`(dataclass, `to_dict`), `for_display` | `graduation/enums.py`, `graduation/data.py` |
| 서비스 | `DegreeAudit`(판정, 대체과목 조회 캐시), `DegreeNumberGenerator`, `ReportCatalog`(정의·조회·CSV·`cell`) | `graduation/services/`, `reporting/services/catalog.py` |
| Action | `RunDegreeAudits`, `WaiveRequirement`(request·approve·reject·lift, `can_decide`/`can_lift`), `GraduateStudents`(handle·batch) | `graduation/actions/` |
| 정책 | `DegreeAuditPolicy`(점검·면제: 졸업 권한자 또는 본인, 쓰기는 Action만) | `graduation/policies.py` |
| 관리 화면 | **졸업 요건 점검**(최신 점검 목록, 필터: 이수 구분·충족·과정·학적 상태, 학번·이름 검색, **점검 실행**, 행 **열기**·**다시 점검**, 일괄 **졸업 처리**), **요건 면제**(대기 기본, 메뉴 배지, **승인**·**반려**·**면제 해제**), 학적 화면 **졸업 요건 점검**(즉시 판정 + **이 점검 저장**)·**요건 면제**, **보고서**, **졸업 설정** | `graduation/admin/`, `graduation/settings_pages.py`, `reporting/admin/`, `person/admin/student_records.py`(믹스인 연결) |
| 포털 | `MyGraduationView`(원본 Livewire `MyGraduation`, 즉시 판정), 메뉴(학생·졸업생) | `graduation/views/portal.py`, `templates/graduation/portal/` |
| 다운로드 | `/reports/<report>.csv`(원본 `ReportCsvController`: `reports.view`, 모르는 보고서 404, `Cache-Control: private, no-store`, `nosniff`) | `reporting/views/csv.py`, `reporting/urls.py` |
| 명령 | `degree_audit_run`(`AuditedCommand`, 결과 기록, `--actor`면 업무 감사 `graduation.audits_run`) | `graduation/management/commands/` |
| 데모 시더 | `DemoGraduationSeeder`: 4학년 재학생(누계 평점 2.5 이상) 3명에게 요건 이수 기록을 가장 오래된 마감 학기에 일괄 삽입(과목마다 `GR` 분반), 영어종합시험 합격 결과, 남는 요건 면제(registrar 요청 → system-administrator 승인), 3학년 이상 점검 저장, 충족한 첫 학생 졸업 | `setup/seeders/demo/graduation.py`, `demo.py` 목록 |
| 매뉴얼 | 관리자 26·27장, 운영 명령 레퍼런스. 4개 언어 | `docs/manual/*/` |
| 번역 | 앱 카탈로그 ko, zh_Hans, lo | `graduation/locale/`, `reporting/locale/` |

## 4. 계획과 달라진 점

| 항목 | 계획/원본 | 실제 | 이유 |
|---|---|---|---|
| 졸업 처리의 쓰기 컨텍스트 | 원본: 요청 사용자 DB 컨텍스트에서 학적 변동·학적 갱신 | 권한 확인(`graduation.process`, 학적 조회 범위, `RecordStatusChange`의 학적 변동 승인 범위) 뒤 트랜잭션 본문만 시스템 컨텍스트(`app.user_id`는 유지) | `student_records` 갱신은 RLS상 `student_records.manage`만 허용한다. 원본은 그 권한 없는 졸업 담당이면 Eloquent 저장이 조용히 0건이 된다(원본 테스트는 사용자 DB 컨텍스트 없이 돌아 드러나지 않음). Django는 `update_fields` 저장이 0건이면 예외를 낸다. Phase 9의 재판정과 같은 판단 |
| 강좌 뷰의 `visible_to` | 계획: `visible_to`가 RLS와 같게 | section_enrollments·section_meetings는 모든 행 | `sections`·`section_meetings`에 RLS가 없어 DB가 모든 행을 준다(테스트로 확인). 수강·대기 인원만 조회자의 RLS를 따른다 |
| headcount의 기본 키 | — | `org_unit_id`를 Django 기본 키로 선언(유일하지 않음), `values()`로만 읽음 | 뷰에 단일 키가 없고, 복합 기본 키는 nullable 칼럼을 받지 않는다(`models.E042`). 스키마 테스트가 nullable을 요구한다 |
| 강좌별 수강 인원의 조직 조건 | 원본: `whereIn('org_unit_id', ...)` | 조직(하위 포함)의 **코드**로 거름 | 뷰에 `org_unit_id`가 없어 원본은 이 조건을 고르면 SQL 오류가 났다 |
| CSV 내보내기 감사 | 원본: 업무 감사 `reports.exported` | + 보안 로그 `data.exported`(보고서, 조건, 행 수) | 계획 11.2 "대량 내보내기 감사". 원본 `SecurityEventType::DataExported`는 정의만 있고 쓰이지 않았다 |
| CSV 시각 표기 | — | `timestamptz`는 PostgreSQL 텍스트처럼 UTC + `+00`(`2026-10-24 07:26:59+00`, 소수 초는 있을 때만), 날짜 `YYYY-MM-DD`, 참/거짓 `Y`/`N` | 조정자가 원본 `laravel_demo` 데이터로 11개 보고서 변형 689행을 비교해 시각 표기만 달랐다(수정 후 일치). 따옴표 방식(PHP `fputcsv`는 공백 있는 칸을 감쌈)과 BOM은 그대로 둔다 |
| 보고서 화면의 조건 칸 | 원본: 보고서를 고르는 즉시 조건 칸이 바뀜(Livewire) | **보기**를 누르면 고른 보고서의 조건 칸이 나타남(GET 폼) | 관리 화면에 자바스크립트 없이 동작하게(시간표 화면과 같은 방식) |
| 모달 동작 | Filament 모달(열기, 다시 점검, 졸업 처리, 면제 결정) | 열기는 별도 화면, 다시 점검은 확인 화면(POST), 졸업 처리는 동작 목록 + 입력 화면, 면제 결정은 의견 입력 화면. 결정할 수 없는 면제의 버튼은 403 | unfold에 모달 폼이 없다(이전 Phase와 같은 방식). 부작용 있는 동작을 GET으로 실행하지 않는다 |
| 포털 메뉴 순서 | 원본 헤더: 기록·성적·출석·시험·졸업·증명서 | `order=44`(시험 42 다음) | 다른 Phase가 쓰는 순서와 겹치지 않게 |
| 데모 이수 기록 | 원본: 팩토리로 한 건씩 | 한 번의 `bulk_create`(같은 규칙, 같은 분반 코드 `GR`), 면제·점검·졸업은 Action | 브리프(대량은 일괄 삽입) |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| 매뉴얼 상대 링크 | 전체 실행에서 `tests/tooling/test_command_documentation.py::test_relative_links_in_the_manuals_resolve`가 `docs/manual/*/README.md`의 `../../README.md` 링크로 실패한다. 이 Phase가 고치지 않은 파일(다른 에이전트 작업 중)이다 | 해당 담당 확인 |
| 원본도 하지 않은 것 | 수료, 졸업유예, 조기졸업, 우등졸업, 학위 종류, 졸업 심사 결재 워크플로, PDF 졸업사정표, 복수전공·부전공 이수 인정 표기 | 요청 시 |
| 범위 부여된 졸업 권한 | `util.has_permission`은 전역 부여만 본다. 조직 범위로만 `graduation.audit`/`graduation.process`를 준 사용자는 앱 검사는 통과해도 점검·면제 쓰기가 RLS에 막힌다(원본과 같음). 기본 역할은 전역 부여다 | 운영 시 역할 설계 |
| headcount `visible_to` | 행(묶음)은 RLS와 같지만 묶음 안의 인원 수는 DB가 센다. 앱에서 셀 일은 없지만 API(Phase 12)는 DB 값을 그대로 쓴다 | Phase 12 |
| unfold 경고 | `get_action_choices()` 시그니처 경고(`RemovedInDjango2028Warning`)는 unfold 라이브러리에서 나온다 | Phase 13 |

## 6. 실행 방법

`uv run manage.py setup_demo --size=small` 후(비밀번호 `demo-password`):

| 계정 | 볼 것 |
|---|---|
| `registrar@demo.test` | 관리 화면 **졸업 > 졸업 요건 점검**: 충족 필터, 점검 열기, **점검 실행**, 학생을 체크하고 **졸업 처리**. 학적 화면의 **졸업 요건 점검**·**요건 면제**. **졸업 > 요건 면제**(상태 필터를 **전체**로 하면 승인된 데모 면제 3건). **보고서 > 보고서**에서 7종과 CSV |
| `system-administrator@demo.test` | registrar가 요청한 면제를 **요건 면제**에서 승인·반려, **설정 > 졸업 설정** |
| `student@demo.test` | 포털 **졸업 요건**: 요건별 이수 과목과 미이수 과목 |

명령 예: `uv run manage.py degree_audit_run --term=<학기 코드> --min-year-level=4 --actor=registrar@demo.test`.

## 7. 검증 결과

| 항목 | 결과 |
|---|---|
| 전체 테스트(`pytest -n 4 -m "not concurrency"`) | 1,065개 중 1,064개 통과(163초). 실패 1개는 5절의 매뉴얼 상대 링크(다른 에이전트가 수정 중인 `docs/manual/*/README.md`) |
| 이 Phase 테스트(`tests/graduation/`, `tests/reporting/`) | 79개 통과(약 60초, tiny 데모를 시딩하는 화면 테스트 4개가 대부분) |
| 원본 오라클 | `laravel-test testing_p11 tests/Feature/Graduation/GraduationTest.php` 4개 통과(106 단언) |
| 정적 검사 | ruff format/check, `tools/checks/raw_sql.py`, `manage.py check`, 이 Phase 앱의 `i18n_missing --strict` 통과. `makemigrations --check --dry-run` 변경 없음 |
| 데모 | 1절 |
