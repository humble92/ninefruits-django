# Phase 9 어학·종합시험 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 9](porting-plan.md#phase-9-어학종합시험-sm), 10절 "시험(ADR 0014)", 원본 [Phase 9 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-9-report.md), 원본 [ADR 0014](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0014-assessments.md), [관리자 매뉴얼 24장](../docs/manual/ko/admin/24-assessments.md)

## 1. 요약

원본의 시험 일반화(CET 어학, SSCORE_ADD 종합시험, COMEXAM 전산을 하나로)를 그대로 옮겼다. 시험 종류가 영역과 판정 방식을 정의하고, 회차(접수 기간, 정원, 합격 점수 override, 결과 공개), 접수(학생 포털·직원, 취소 행 되살림, 결시), 결과(영역 점수, 자동 합격 판정을 `is_passed`에 저장, 재입력 교체, CSV 가져오기), 공개 뒤 잠금과 정정 요청(요청자≠결정자), 공개 전 합격 점수 변경과 재판정, 외부 성적(증빙 파일 `Media`), 졸업 요건 종류 **시험 합격**(`curriculum_requirements.assessment_type`을 `AssessmentType` 외래 키로 전환)을 구현했다. 관리 화면 4개(시험 회차와 응시자 탭, 시험 결과, 결과 정정 요청, 시험 종류와 영역), 포털 **어학/종합시험**, 증빙 다운로드, 명령 2개, 프로파일 단계(종류 4개), 데모 시더(일괄 삽입), 관리자 매뉴얼 24장(4개 언어), 운영 명령 레퍼런스, 번역(앱 카탈로그 142개 항목)을 더했다.

- 이 Phase에서 추가한 테스트 30개(`tests/assessment/`) 통과. 원본 `AssessmentTest`의 9개 사례를 모두 옮겼다. 전체 결과는 7절.
- 빈 DB에서 `setup_install --force --profile=korean-university`와 `setup_demo --size=small --seed=42`(13.0초, 데모 전체, 시험 시더 약 1초) 성공. 데모: 시험 종류 4개(영역 4개), 회차 4개(지난 영어 회차 2개와 전산 회차 1개는 결과 공개, 접수 중인 영어 회차 1개), 접수 61건(결시 4), 결과 55건(외부 TOPIK 4건, 합격 39~41건), 영역 점수 144건, 교육과정 5개에 시험 합격 요건. 원본 small(Phase 9 보고: 접수 61건, 결시 2, 결과 57건, 합격 42건)과 같은 수준이다.

## 2. 완료 기준

계획서 Phase 9 항목

| 항목 | 결과 | 근거 |
|---|---|---|
| 종류·영역·판정 | 충족 | `AssessmentType`, `AssessmentComponent`(종류 × 코드 unique). 점수 종류: 총점 ≥ 합격 점수(회차 값 우선) ∧ 모든 영역 ≥ 최저점, 합격 점수가 없거나 합격/불합격 종류는 담당자 판정. 판정은 `is_passed`에 저장(`test_decides_passes_...`, 영역 최저점 경계 테스트) |
| 회차·접수·정원 | 충족 | 회차 외래 키 `on_delete=PROTECT`(DB도 restrict, `test_the_schema_restricts_deleting_a_session_with_registrations`), 학생 접수는 기간·정원·중복·재학 상태 확인 뒤 시스템 컨텍스트로 기록, 직원 접수는 시험일까지, 시험일 지난 회차 접수 불가 |
| 결과 입력·CSV·공개·잠금 | 충족 | `RecordAssessmentResult`(입력·외부·삭제·공개), `AssessmentResultImporter`(화면과 명령 공용, 미접수·모르는 학번·점수 오류 행 보고), 공개 뒤 입력·삭제 거부 |
| 정정 승인(직무 분리) | 충족 | `CorrectAssessmentResult`(요청·승인·반려·취소, 본인 결정 거부, 결과당 대기 요청 하나: 부분 unique), 승인 시 같은 트랜잭션에서 반영(감사 `assessment.result_corrected`) |
| 외부 성적·증빙 | 충족 | 증빙 컬렉션 `evidence`(PDF, JPG, PNG, 5MB, MIME 검사), `/assessment-results/<id>/evidence/`(정책: 기록·관리 권한자 또는 본인) |
| 졸업 요건 연계 | 충족 | `CurriculumRequirement.assessment_type` 외래 키(상태 전용 마이그레이션 `curriculum/0003_p9_assessment_type_fk`, 열 그대로), 요건 편집 화면의 시험 종류 선택, `AssessmentPassCheck.has_passed/required`, CHECK 제약 테스트 |
| 포털 접수·조회 | 충족 | `/portal/assessments/`(요건과 합격 여부, 접수 중인 회차 접수·취소, 내 접수, 내 결과와 증빙), HTMX 블록 교체, 메뉴(학생·졸업생) |
| RLS와 `visible_to` | 충족 | 접수·결과·영역 점수·정정 4개 표 × 사용자 8종에서 일치(`test_assessment_access.py`). `util.has_permission`이 전역 부여만 보므로 결과의 직원 조회도 전역 `assessments.record/manage`만 인정 |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `assessment_import_results`(`--dry-run`, 오류 행 종료 코드 2), `assessment_publish_results` + `test_imports_results_from_a_csv_and_reports_problems` |
| 2. 매뉴얼 | 관리자 매뉴얼 24장 4개 언어(원본 장 + "이 설치본의 화면" 절), 운영 명령 레퍼런스 4개 언어 |
| 3. 시더, 팩토리, 데모 | 프로파일 단계 `korean_university_assessments.seed_assessment_types`(멱등·관리자 수정 보존 테스트), 팩토리 `tests/factories/assessment.py`(원본에는 없음), 데모 `DemoAssessmentSeeder`(일괄 삽입). 원본에 시험 필수 시더는 없다 |
| 4. `setup_install`, `setup_demo --size=small` | 빈 DB에서 성공(5절의 저장소 주의 참고) |
| 5. 번역 | `ninefruits/assessment/locale/` 142개 항목, `convert_translations.py --fill`로 원본 값 채움(원본 그룹 `assessment`, `validation` 등). 다른 카탈로그에 있던 3개는 그 번역을 옮김. `i18n_missing --strict` 통과 |
| 6. 스키마 동등성 | 통과. 상태 전용 마이그레이션 `assessment/0001_initial`, `curriculum/0003_p9_assessment_type_fk`. 스키마 변경 없음. unique 제약 5개와 부분 unique 인덱스 1개는 같은 이름으로 `Meta`에 문서로 선언 |
| 7. 테스트 대응표 | `AssessmentTest` 완료, `AdminPagesTest` 행에 이 Phase 화면 추가(원본 `AdminPagesTest`에는 시험 데이터셋이 없어 화면 렌더링은 `test_assessment_admin.py`가 맡음) |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 모델 | `AssessmentType`, `AssessmentComponent`, `AssessmentSession`, `AssessmentRegistration`, `AssessmentResult`(`HasMedia`, 증빙 컬렉션), `AssessmentComponentScore`, `AssessmentResultCorrection`. 원본 열 이름은 `db_column`(`assessment_session_id` 등) | `ninefruits/assessment/models/` |
| 범위 조회 | `AssessmentRegistration.visible_to`(볼 수 있는 학적), `AssessmentResult.visible_to`(전역 기록·관리 권한자는 볼 수 있는 학적, 학생은 본인의 공개된 회차 결과와 외부 성적), 영역 점수·정정은 볼 수 있는 결과. 종류·영역·회차는 설정 데이터 | `models/`, `tests/assessment/test_assessment_access.py` |
| 열거형 | `AssessmentCategory`, `ScoringMethod`, `AssessmentRegistrationStatus`, `CorrectionStatus`, `ResultSource` | `assessment/enums.py` |
| Action | `RegisterForAssessment`(register·cancel·mark_absent), `RecordAssessmentResult`(for_registration·external·remove·publish), `CorrectAssessmentResult`(request·approve·reject·cancel), `ChangeSessionPassScore` | `assessment/actions/` |
| 서비스 | `AssessmentPassCheck`(Phase 11 졸업 사정이 호출), `AssessmentResultImporter`(UTF-8/BOM CSV, 열 이름 대소문자 무관, 줄 번호는 머리글 포함) | `assessment/services/` |
| 정책 | 종류·영역·회차: 기준정보 정책(`assessments.manage`), 접수·결과·영역 점수·정정: 읽기 전용(기록·관리 권한자 또는 본인), 변경은 Action으로 | `assessment/policies.py` |
| 관리 화면 | **시험 회차**(목록 행: 결과 공개, 결과 가져오기 / 화면 버튼: 학생 접수, 결과 가져오기, 결과 공개 / **응시자** 탭: 상태 필터, 행별 결과 입력·정정 요청·결시·접수 취소 / 합격 점수 변경은 `ChangeSessionPassScore`로, 공개 뒤 읽기 전용), **시험 결과**(외부 성적 등록, 증빙 링크, 삭제, 종류·출처·합격 필터, 학번·이름 검색), **결과 정정 요청**(대기 기본, 메뉴 배지, 승인·반려·요청 취소), **시험 종류**(영역 탭) | `assessment/admin/` |
| 졸업 요건 화면 | 요건 편집의 시험 종류를 사용 중인 종류의 외래 키 선택으로(원본 `CurriculumRequirementSetResource`) | `curriculum/admin/requirements.py` |
| 포털 | `MyAssessmentsView`(원본 Livewire `MyAssessments`), 버튼은 폼(자바스크립트 없이 동작), HTMX면 `#assessments` 교체 | `assessment/views/portal.py`, `templates/assessment/portal/` |
| 다운로드 | `EvidenceDownloadView`(`PrivateMediaDownloadView`, inline, `nosniff`, `private, no-store`) | `assessment/views/evidence.py` |
| 명령 | `assessment_import_results`, `assessment_publish_results`(`AuditedCommand`, `--actor` 필수) | `assessment/management/commands/` |
| 시더 | 프로파일 단계(종류 4개, 영어 영역 4개), 데모(지난 회차 접수·결과·영역 점수 일괄 삽입, 공개·접수 중 회차 접수·외부 성적은 Action, 교육과정 요건) | `setup/seeders/profiles/korean_university_assessments.py`, `setup/seeders/demo/assessment.py` |
| 매뉴얼 | 관리자 24장, 운영 명령 레퍼런스. 4개 언어 | `docs/manual/*/` |

### 데모 시더 속도

원본은 지난 회차 결과를 한 건씩 Action으로 입력했다. 이식본은 같은 판정 규칙으로 메모리에서 정해 접수·결과·영역 점수를 일괄 삽입하고, 공개(3회), 접수 중 회차 접수(6건), 외부 성적(4건)만 Action을 거친다. 원본처럼 재학생 40명(small 기준)을 골라 쓰므로 크기와 관계없이 행 수가 같다(tiny는 같은 비율로 줄임). 같은 기계, 빈 DB에서: 시험 시더 small 약 1초, `setup_demo` 전체 small 13.0초, medium 30.6초(시험 행 수 동일).

## 4. 계획과 달라진 점

| 항목 | 계획/원본 | 실제 | 이유 |
|---|---|---|---|
| 학생 접수의 정원 계산 | 원본: 요청 사용자 DB 컨텍스트에서 회차의 활성 접수를 센다 | 회차 행을 잠그고(`select_for_update`) 시스템 컨텍스트에서 세고 기록한다. 학생 취소의 "결과 있음" 확인도 시스템 컨텍스트 | RLS 아래 학생은 자기 접수만 보므로 원본 방식이면 정원이 사실상 적용되지 않는다(테스트에서 확인). 잠금으로 동시 접수 초과도 막는다 |
| 합격 점수 변경의 재판정 | 원본: 요청 사용자 컨텍스트에서 결과 갱신 | 권한 확인 뒤 재판정만 시스템 컨텍스트 | 결과 쓰기 정책은 `assessments.record` 전역만 허용한다. `assessments.manage`만 가진 담당자가 바꾸면 원본은 RLS가 갱신을 조용히 0건으로 만든다. 저장된 점수에서 나오는 파생 값이다(Phase 6 학기 기록과 같은 판단) |
| 결과 조회의 직원 범위 | 원본 앱: `can('assessments.record')`(범위 부여 포함) | `visible_to`는 RLS처럼 전역 부여만 인정 | 계획 7.4절(앱 범위 = RLS). 조직 범위만 가진 기록 담당은 원본에서도 DB가 결과를 숨긴다 |
| 보이지 않는 결과의 증빙 | 원본: 라우트 바인딩 후 정책 403 | 볼 수 없는 결과(없는 결과 포함)는 403 | 존재 여부를 드러내지 않으면서 원본 테스트(남의 증빙 403)와 같게 |
| 관계 관리자 | Filament `RegistrationsRelationManager`, `ComponentsRelationManager`, 모달 액션 | 회차 화면의 **응시자** 탭(행 링크 → 입력 화면), 종류 화면의 **영역** 탭(인라인), 목록 행·화면 버튼 | unfold에 관계 관리자·모달 폼이 없다(Phase 5 수강생 탭과 같은 방식). 행 링크는 상태에 따라 보이고, 버튼은 실행 화면에서 다시 확인한다 |
| CSV 가져오기 등록 | 브리프: 원본이 Filament Importer면 `ninefruits.importing`에 등록 | 등록하지 않음 | 원본은 Importer가 아니라 회차 단위 도메인 서비스(`AssessmentResultImporter`)다. `imports` 표를 쓰지 않고 결과를 바로 알린다(원본과 같음) |
| 프로파일 멱등 | 원본: 종류가 하나라도 있으면 건너뜀 | 코드별 `seed_row`(없는 종류와 번역만 추가), 영역은 종류를 새로 만들 때만 | 다른 프로파일 단계와 같은 멱등 규칙. 관리자가 지운 영역은 되살리지 않는다 |
| 데모 생성 | 원본: 지난 회차 결과를 한 건씩 Action | 일괄 삽입(같은 판정 규칙), 결과마다의 업무 감사는 남기지 않음 | 브리프(대량은 bulk). 공개·접수·외부 성적은 Action을 거쳐 감사가 남는다 |
| 점수 자릿수 | 원본: `float` 비교 후 `decimal(6,1)` 저장 | `Decimal`로 비교, 저장 전 0.1 단위 반올림(PostgreSQL과 같은 half-up) | 부동소수점 없이 같은 결과 |
| CSV `note` 빈 칸 | 원본: 빈 문자열 저장 | `NULL` | 화면 입력과 같은 표현. 표시 차이 없음 |
| 매뉴얼 FAQ | 원본 FAQ: "이미 입력한 결과는 다시 입력해야 새 기준" | "새 기준으로 바로 다시 판정" | 원본 4a절 변경(재판정)과 FAQ가 어긋나 있었다. 코드를 따랐다 |
| 포털 메뉴 순서 | 원본 헤더: 기록·성적·출석·시험·졸업·증명서 | `order=42`(성적 30과 수강신청 50 사이) | 다른 Phase가 쓰는 순서와 겹치지 않게 |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| 졸업 사정 연결 | `DegreeAudit`의 `assessment_pass` 요건이 `AssessmentPassCheck.has_passed`를 호출, 졸업 데모 시더의 추가 영어 회차(원본 `DemoGraduationSeeder`) | Phase 11 |
| 면제 화면의 요건 이름 | 원본 `ViewStudentRecord` 면제 요건 목록이 시험 종류 이름을 쓴다 | Phase 11 |
| `setup_demo` 저장소 충돌 | 비공개 저장소(`storage/private`)에 다른 DB의 `<media id>/` 디렉터리가 남아 있으면 증명서 데모 시더(Phase 8)가 "Media path is already taken"으로 멈춘다. 빈 저장소(`PRIVATE_MEDIA_ROOT`를 새 디렉터리로)에서는 small·medium 모두 성공했다 | Phase 8 담당 확인(데모 전 저장소 정리 또는 경로 충돌 처리) |
| 원본도 하지 않은 것 | 응시료, 좌석 배정, 학생의 외부 성적 직접 제출, 결과 공개 알림 메일, 외부 시험 등급별 합격 기준 표 | 요청 시 |
| mypy | unfold 데코레이터의 untyped 경고 등 다른 앱과 같은 수준(CI는 아직 mypy를 강제하지 않음) | Phase 13 |

## 6. 실행 방법

`uv run manage.py setup_demo --size=small` 후(비밀번호 `demo-password`):

| 계정 | 볼 것 |
|---|---|
| `registrar@demo.test` | 관리 화면 **어학/종합시험 > 시험 회차**: 접수 중인 영어 회차의 **응시자** 탭(결과 입력, 결시, 접수 취소), **학생 접수**, **결과 가져오기(CSV)**. 지난 회차는 공개되어 **정정 요청**만 보인다. **시험 결과**에서 **외부 성적 등록**(증빙 PDF) |
| `academic-affairs@demo.test` | registrar가 올린 정정 요청을 **결과 정정 요청**에서 승인·반려, **시험 종류**의 영역, 회차 합격 점수 변경(공개 전) |
| `student@demo.test` | 포털 **어학/종합시험**: 교육과정의 영어종합시험 요건, 접수 중인 회차 접수·취소, 공개된 결과 |

명령 예: `uv run manage.py assessment_import_results ENG_COMP 2026-11-28 eng.csv --actor=registrar@demo.test --dry-run`, `uv run manage.py assessment_publish_results ENG_COMP 2026-11-28 --actor=registrar@demo.test`.

## 7. 검증 결과

| 항목 | 결과 |
|---|---|
| 전체 테스트(`pytest -n 4 -m "not concurrency"`) | 940개 통과(104초). 다른 Phase(7, 8, 10) 작업 중의 상태 |
| 이 Phase 테스트(`tests/assessment/`) | 30개 통과(약 60초, tiny 데모를 시딩하는 관리 화면 테스트 8개가 대부분) |
| 원본 오라클 | `laravel-test testing_p9 tests/Feature/Assessment/AssessmentTest.php` 9개 통과(같은 사례를 옮김) |
| 정적 검사 | ruff format/check, `tools/checks/raw_sql.py`, `manage.py check`, `naming_check`, `i18n_missing --strict` 통과. `makemigrations --check --dry-run` 변경 없음 |
| 데모 | 1절, 3절 |
