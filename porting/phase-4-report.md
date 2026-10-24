# Phase 4 교육과정과 개설강좌 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 4](porting-plan.md#phase-4-교육과정과-개설강좌-l), 원본 [Phase 4 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-4-report.md), 원본 [ADR 0009](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0009-courses-sections-and-sessions.md)

## 1. 요약

교과목(기간별 버전, 선수·동시수강 과목, 대체과목), 이수 구분별 졸업 요건(교육과정 연도), 교과목 CSV 가져오기, 개설강좌(담당 교원, 강의 시간·강의실, 수강 대상·제외 대상, 좌석 할당), 강의실·교원 중복 배정의 설명, 시간표(강의실·교원, 휴대폰 목록), 강의계획서, 이전 학기 복사, 명령 2개, 관리 화면, 포털 화면 4개(개설강좌 조회, 강좌 상세, 강의계획서 작성, 담당 강좌), 데모 교육과정을 구현했다. 학기 세션은 Phase 1에서 이미 이식되어 있었다. 복수전공·부전공 신청·승인은 같은 Phase의 다른 작업자(p2) 범위다.

- 이 Phase에서 추가한 테스트 37개(교육과정 11, 개설강좌 26) 통과. 전체 619개 통과(`-n 4` 36초). ruff format/check, raw SQL 검사, `manage.py check`, `makemigrations --check`, `naming_check`, 스키마 동등성·모델 열 일치 검사 통과. `i18n_missing --strict`에서 이 Phase 카탈로그(curriculum, offering, grading)의 누락은 0이다(남은 1건은 Phase 2 작업 중 문구).
- 빈 DB에서 `setup_install --force --profile=korean-university`(2초), `setup_demo --size=small --seed=42`(1.7초) 성공. 데모 두 학기(각 52개 강좌)가 `schedule_check_conflicts`에서 문제 0건. 데모 행 수는 원본 small 데모와 같다(교과목 47, 버전 48, 선수과목 30, 대체과목 1, 졸업 요건 12, 요건 과목 96, 세션 5). 강좌·강의 시간·좌석·강의계획서 수의 차이는 원본의 Phase 6 성적 이력 시더가 만든 지난 학기 강좌 때문이다.

## 2. 완료 기준

| 완료 기준 | 결과 | 근거 |
|---|---|---|
| 과목 버전 기간 중복 차단 | 충족 | `tests/curriculum/test_course.py`: 겹치는 버전은 DB 배제 제약(`course_versions_no_overlap_excl`)이 거부. 개정은 이전 버전을 전날 끝내고 선수과목을 복사. CSV로 겹치는 버전을 넣으면 그 행만 실패. 관리 화면은 저장 전에 겹침을 안내(`tests/curriculum/test_curriculum_admin.py`) |
| 강의실/교원 시간 중복 배정 차단 | 충족 | `tests/offering/test_schedule_conflict.py`: 강의실은 배제 제약, 교원은 두 테이블의 트리거로 DB가 거부. 배정 순서를 바꿔도, ORM을 거치지 않는 INSERT도 차단. 전·후반기는 같은 시간과 강의실 사용 가능. 폐강하면 비워지고 다시 열면 다시 검사. 메시지에 겹치는 강좌 표시. 관리 화면 강의 시간 탭에서도 같은 안내(`tests/offering/test_curriculum_admin.py`) |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `section_copy`, `schedule_check_conflicts`, `reference_import courses` + 테스트 |
| 2. 매뉴얼 | 운영 명령 레퍼런스 4개 언어(`reference_import` 유형에 `courses` 추가), 관리자 매뉴얼 17~19장 4개 언어 |
| 3. 시더, 팩토리, 데모 | 필수 시더 변경 없음(이 Phase의 기준 데이터는 프로파일의 교과 구분). 팩토리: `CourseFactory`, `CourseVersionFactory`, `CurriculumRequirementSetFactory`, `SectionFactory`. 데모 교육과정 시더(일괄 삽입) |
| 4. `setup_install`, `setup_demo --size=small` | 빈 DB에서 성공 |
| 5. 번역 | 앱 카탈로그 `curriculum`, `offering`(신설), `grading`(평가 방식 2개) 채움. 원본에 없는 문구 5개는 직접 번역 |
| 6. 스키마 동등성 | 통과(도메인 마이그레이션은 상태 전용: `curriculum/0002_courses_and_requirements`, `offering/0001_initial`) |
| 7. 테스트 대응표 | `CourseTest`, `SectionActionsTest`, `ScheduleConflictTest` 완료, `CurriculumAdminTest` 부분(복수전공·부전공 2개 사례는 Phase 2), `AdminPagesTest` 행에 이 Phase 화면 추가 |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 교과목과 버전 | `Course`, `CourseVersion`(`version_on`, `label`, 개정 대상 속성 `ATTRIBUTES`), `CourseRequisite`, `CourseEquivalency`. 열거형 `GradingBasis`, `RequisiteKind`, `ProgramRole`, `RequirementKind` | `ninefruits/curriculum/models/course.py`, `enums.py` |
| 졸업 요건 | `CurriculumRequirementSet`(`for_catalog_year`, `overlapping`, `applicable`), `CurriculumRequirement`, 중간 테이블 `CurriculumRequirementCourse`. `assessment_type_id`는 Phase 9 모델이 생길 때까지 숫자 열 | `curriculum/models/requirement.py` |
| 교과목 Action | `CreateCourse`, `ReviseCourse`(감사 `course.created`, `course.revised`) | `curriculum/actions/` |
| 교과목 CSV | `CourseResource`(원본 `CourseImporter` 열과 규칙, 새 교과목은 행 세이브포인트 안에서 생성), 등록기 유형 `courses`(권한 `courses.manage`) | `curriculum/importers.py` |
| 정책 | 교과목·버전·선수과목·대체과목 `courses.manage`, 졸업 요건 `curriculum.manage`(조회는 `reference_data.view`), `SectionPolicy`(조회, 생성, 수정, `edit_syllabus`, 작성 중만 삭제), 강좌 하위 행 정책 | `curriculum/policies.py`, `offering/policies.py` |
| 개설강좌 모델 | `Section`(`manageable_by`, `in_scope_of`, `visible_to`, `taught_by`, `admits`, `is_manageable_by`, `is_taught_by`), `SectionInstructor`, `SectionMeeting`(벽시계 시각), `SectionSeatGroup`(`is_reserved_at`), `Syllabus`. 복합 외래 키(세션·학기, 버전·교과목)는 DB 그대로, 모델은 `db_constraint=False` | `ninefruits/offering/models/section.py` |
| 개설강좌 Action | `CreateSection`, `UpdateSection`(세션 이동 시 버전·강의 날짜 이동, 정원 행 잠금), `AssignSectionInstructor`, `ChangeSectionStatus`(폐강 사유, 감사 `section.<status>`, `SectionPublished` 이벤트), `SaveSectionMeeting`, `UpdateSyllabus`(원본 검증 규칙), `CopySections` + `SectionCopyReport`(미리 보기는 트랜잭션 되돌림) | `offering/actions/` |
| 충돌 설명 | `ScheduleConflicts.guard`: 세이브포인트에서 실행하고 23P01(배제 제약, 교원 트리거)을 겹치는 강좌 이름이 든 `ValidationError`로 바꾼다. 강의실은 배제 위반 DETAIL의 기존 키로 강좌를 찾는다(SQL 없이 ORM 조회) | `offering/services/schedule_conflicts.py` |
| 시간표 | `Timetable.build`(30분 단위, 월~금 항상), `summary`, `weekday_label`, `room_label`. 공용 템플릿(휴대폰은 요일별 목록, 큰 화면은 주간 격자, 관리 화면과 포털 같은 모양) | `offering/services/timetable.py`, `templates/offering/partials/timetable.html` |
| 이벤트 | `SectionPublished`(dataclass, `core.events.dispatch`). LMS 리스너는 Phase 12 | `offering/events.py` |
| 관리 화면 | 교과목(버전 탭, 대체과목 탭, 날짜부터 개정 화면, CSV 가져오기, 첫 버전과 함께 생성), 교과목 버전(선수·동시수강 인라인, 사이드바 숨김), 졸업 요건(요건 인라인, 종류별 입력 검증, 적용 연도 겹침 안내), 개설강좌(학기 기본 필터, 권한 범위 목록, 강의 시간·담당 교원·좌석 할당 탭, 수강 대상·제외 대상, 공개/작성 중으로/폐강/다시 열기 버튼, 강의계획서 버튼, 다른 학기에서 복사), 시간표 페이지 | `curriculum/admin/`, `offering/admin/` |
| 포털 | 개설강좌 조회(학기·조직·검색, HTMX 부분 갱신, 25개씩), 강좌 상세(선수과목 묶음, 공개 강의계획서, 담당자에게 초안), 강의계획서 작성(평가 항목 추가·삭제는 서버 왕복, 주차 수는 세션 기간), 담당 강좌(교원 시간표, 강의계획서 상태). 메뉴: 개설강좌(인물이 있는 계정), 담당 강좌(교원 persona) | `offering/views/portal.py`, `offering/portal_urls.py`, `templates/offering/portal/` |
| 담당 강좌 확장 | 이후 Phase가 출석·성적 입력·강의평가·LMS 열을 등록하는 `offering.teaching.register_column` | `offering/teaching.py` |
| 명령 | `section_copy`(AuditedCommand, `--actor` 필수, `--org-unit` 반복, `--dry-run`), `schedule_check_conflicts`(StatusCommand, 종료 코드 2) | `offering/management/commands/` |
| 데모 | `DemoCurriculumSeeder`: 원본과 같은 교과목·개정·대체과목·선수과목·졸업 요건·전후반기 세션(업무 기간 복사)·강좌 편성 규칙, 다음 학기는 `CopySections`로 복사 후 공개. 교과목·버전·선수과목·요건 과목·강좌·담당 교원·강의 시간·좌석·강의계획서는 `bulk_create` | `ninefruits/setup/seeders/demo/curriculum.py` |
| 매뉴얼 | 관리자 17~19장(원본 장 + Django 화면 차이: 버전 화면, CSV 가져오기 절, 권한 범위 절, `uv run manage.py` 명령), 운영 명령 레퍼런스 | `docs/manual/*/` |

## 4. 계획과 달라진 점

| 항목 | 계획/원본 | 실제 | 이유 |
|---|---|---|---|
| 복수전공·부전공 | 계획 Phase 4 | p2 작업(Phase 2 앱 `person`) | 작업 분담. 원본 데모 시더의 복수전공·부전공 신청 부분(`additionalPrograms`)도 넣지 않았다. 19장 매뉴얼은 원본 화면 이름으로 옮겼다 |
| 학생 시간표 | 계획 Phase 4 | Phase 5 | 원본과 같다(수강 데이터가 Phase 5). `Timetable` 서비스와 공용 템플릿은 준비됨 |
| 버전 편집 위치 | 원본: 교과목 화면 관계 관리자의 모달(선수과목 반복 입력 포함) | 교과목 화면 버전 탭(목록) + 버전 화면(선수과목 인라인) | Django admin은 중첩 인라인이 없다. 버전 화면은 사이드바에 넣지 않는다(`navigation_hidden`) |
| 강의 시간·담당 교원 저장 | 원본: 관계 관리자 행 작업 | 개설강좌 화면 탭(인라인)이 Action을 거쳐 저장하고, 거부되면 메시지로 안내 | 화면 상태가 아니라 Action이 판단(원본과 같은 원칙) |
| 교시로 시각 채우기 | 원본: 실시간 입력 | 교시를 고르면 비어 있는 시작·종료 시각을 저장할 때 채움 | 서버 렌더링 |
| 강의계획서 평가 항목 추가 | 원본: Livewire | 폼 제출(저장하지 않고 다시 그림) | 자바스크립트 없이 동작 |
| `Section::visible_to` | 원본: `constrainManageableBy`(직원 범위) | `manageable_by`(관리 화면) + `visible_to`(직원 범위 ∪ 공개 강좌 ∪ 본인 담당) | 포털 화면도 `visible_to`를 거치는 규칙(CLAUDE.md) |
| 강좌 상세의 LMS 링크 | 원본 v1.0.0에 있음 | Phase 12 | LMS 테이블 모델이 아직 없다 |
| `UpdateSection`의 성적 입력 확인 | 원본: `enrollments.grade_status` | `registration.Enrollment` 모델이 있을 때만 확인 | Phase 5·6 모델 |
| 수강 대상 입력의 학업 상태 | 원본 `TargetCriteriaFields` | 학년, 입학 연도, 프로그램, 조직만(좌석 할당도 같음) | 원본 개설강좌 화면과 같은 항목 |
| `importing.registry` | Phase 1: 등록기가 비어 있을 때만 기본 유형 적재 | 기본 유형 적재 여부를 따로 기억 | 앱 `ready()`에서 등록하면 기본 5종이 사라지는 문제(이 Phase에서 발견해 수정) |
| 평가 방식 열거형 | Phase 6 | `grading.enums.EvaluationMethod`를 이번에 추가 | `sections.evaluation_method` 입력에 필요 |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| 수강신청 적용 | 수강 대상·제외 대상, 좌석 할당, 선수과목(대체과목 포함), 학생 시간표 | Phase 5 |
| 개설강좌 화면의 수강생·대기자·수업 회차 탭 | 원본 `RosterRelationManager`, `WaitlistRelationManager`, `ClassMeetingsRelationManager` | Phase 5, 10 |
| 담당 강좌 열 | 출석, 성적 입력, 강의평가 결과, LMS 링크(`teaching.register_column`) | Phase 6, 7, 10, 12 |
| `SectionPublished` 리스너 | LMS 강좌 생성 | Phase 12 |
| 졸업 요건 판정, 시험 합격 요건 | `assessment_type_id`를 외래 키로, 요건 화면의 시험 종류 선택 | Phase 9, 11 |
| 복수전공·부전공 데모 신청 | 원본 데모 시더 마지막 단계 | Phase 2(p2) |
| 관리 화면 캡처 | 매뉴얼 화면 캡처 | Phase 13 |
| 다른 작업자 파일 | `tests/factories/person.py`의 ruff 위반 2건(줄 길이), 전역 카탈로그 누락 1건은 p2 작업 중 | p2 |
