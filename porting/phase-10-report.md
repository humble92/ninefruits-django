# Phase 10 교수 강의실과 출석 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 10](porting-plan.md#phase-10-교수-강의실과-출석-sm), 10절 "출석(ADR 0015)", 원본 [Phase 10 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-10-report.md), 원본 [ADR 0015](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0015-attendance.md), [관리자 매뉴얼 25장](../docs/manual/ko/admin/25-classroom-and-attendance.md)

## 1. 요약

교원 포털 **수강생과 출석** 화면(사진 포함 명단과 출석 합계, 명단 CSV, 출석부 PDF, 수업 회차 생성·추가·휴강·되돌리기, 회차별 출석 입력과 전원 출석), 학생 포털 **출석** 화면, 관리 화면 개설강좌의 **수업 회차** 탭(Phase 4가 남긴 것: 회차 생성, 휴강, 되돌리기), 집계 서비스 `AttendanceSummary` 한 곳, 명단 서비스 `SectionRoster`(CSV 수식 주입 방지), 명령 `attendance_generate_sessions`, 데모 출석 시더(일괄 삽입), 관리자 매뉴얼 25장(4개 언어), 번역을 구현했다. 표 `class_meetings`, `attendance_records`, RLS 정책과 `SECURITY DEFINER` 함수 `util.taught_student_record_ids()`는 Phase 0의 스키마 재생(`core/0043`)으로 이미 있고, 이 Phase는 상태 전용 마이그레이션 `attendance/0001_initial`로 모델을 맞췄다. 교원의 수강생 학적 조회 범위(`StudentRecord.visible_to`)는 Phase 2가 이미 함수와 같은 조건으로 넣어 두었고, 이 Phase에서 출석 기록·회차의 애플리케이션 범위를 RLS와 같게 만들고 테스트로 확인했다.

- 이 Phase에서 추가한 테스트 13개(`tests/attendance/`) 통과. 원본 `AttendanceTest`의 5개 사례를 모두 옮기고(원본은 오라클로 실행해 5개 통과 확인), 휴강 사유, 출석률 반올림, 학생 화면 집계, 명단 CSV 수식 방지, 관리 화면 탭, tiny 데모 화면(영어·한국어) 사례를 더했다. 전체 결과는 7절.
- 빈 DB에서 `setup_install --force --profile=korean-university`(2.5초)와 `setup_demo --size=small --seed=42 --force`(14.4초, 다른 Phase 시더 포함) 성공. 출석 시더 1.3초: 이번 학기 52개 강좌의 수업 회차 1,404개, 출석 기록 3,820건(출석 3,257 · 지각 282 · 결석 205 · 공결 76), 강좌 다섯 중 하나는 최근 진행 회차 미입력. 원본 small 데모(회차 1,404개, 기록 3,609건: 출석 3,060 · 지각 281 · 결석 183 · 공결 85)와 같은 수준이다.

## 2. 완료 기준

원본 계획 10.9절 항목

| 항목 | 결과 | 근거 |
|---|---|---|
| 담당 강좌 목록 | 충족 | Phase 4의 **담당 강좌** 화면에 `teaching.register_column("attendance", ...)`로 **수강생과 출석** 열 추가(성적 입력 열 앞) |
| 수강생 명단(사진, 권한 범위 내) | 충족 | 사진(있는 사람만, 사진 다운로드 뷰), 학번, 이름, 과정, 학년 + 출석 합계·출석률. 담당 교원과 `sections.view`/`sections.manage` 범위 직원만(`SectionRoster.can_view`), 그 밖에는 403 |
| 명단 CSV | 충족 | UTF-8 BOM, `=`·`+`·`-`·`@`·탭·CR로 시작하는 칸은 작은따옴표(원본 `ReportCatalog::cell`과 같은 규칙, `spreadsheet_cell`), 감사 `attendance.roster_exported`, `Cache-Control: private, no-store`, `nosniff` |
| 수업 회차(강의 시간 기준, 멱등) | 충족 | `GenerateClassMeetings.for_section/for_term`: 강의 시간의 요일·기간으로 없을 때만 만든다(강좌당 일괄 삽입). 교원 버튼, 관리 화면 버튼, 명령. 보강 추가(세션 기간, 중복 거부), 휴강(사유 필수)·되돌리기 |
| 출석/지각/결석/공결 입력 | 충족 | `RecordAttendance.save`: 바뀐 학생만 쓰고 비우면 삭제, 감사 `attendance.recorded`에 학생별 (이전, 이후). 미래 회차·휴강 회차·미수강생·잘못된 상태 거부. 포털 HTMX 폼(전원 출석은 저장 없이 표시) |
| 출석부 PDF | 충족 | `ninefruits.pdf`(Gotenberg) 가로 A4, 학생 × 회차(휴강 제외), O/△/X/공, 학생별 합계, 감사 `attendance.sheet_exported`. Gotenberg 오류는 503 안내 |
| 학생 출석 조회 | 충족 | `/portal/attendance/`: 학기 선택(기본: 시작한 가장 최근 학기), 과목별 합계·출석률, 진행 회차별 기록 |
| 교원용 RLS와 `SECURITY DEFINER` 함수 | 충족 | DB에 이미 있음. `AttendanceRecord.visible_to`(볼 수 있는 수강), `ClassMeeting.visible_to`(로그인 사용자), `StudentRecord.visible_to`(담당 강좌 수강생, Phase 2)가 교원·학생·무관한 교원 세 경우에서 RLS와 같은 결과(테스트) |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `attendance_generate_sessions`(`--section`, `--dry-run`, 종료 코드 1: 없는 학기) + `test_attendance.py` |
| 2. 매뉴얼 | 관리자 매뉴얼 25장 4개 언어(원본 장 + "이 설치본의 화면" 절), 운영 명령 레퍼런스 4개 언어 |
| 3. 시더, 팩토리, 데모 | 데모 `DemoAttendanceSeeder`(일괄 삽입, `--seed` 재현, 다시 실행하면 아무것도 하지 않음). 원본에 출석 필수 시더·팩토리는 없다(테스트는 Action으로 만든다) |
| 4. `setup_install`, `setup_demo --size=small` | 빈 DB에서 성공 |
| 5. 번역 | `ninefruits/attendance/locale/` 87개 항목, `convert_translations.py --fill`로 원본 값 채움(원본에 없는 모델 이름 3개와 PDF 오류 문구는 직접/성적 앱 번역). `i18n_missing --strict`에 이 앱 문제 없음 |
| 6. 스키마 동등성 | 통과. 상태 전용 마이그레이션 `attendance/0001_initial`. unique 제약 2개는 같은 이름으로 `Meta`에 문서로 선언. 스키마 변경 없음 |
| 7. 테스트 대응표 | `AttendanceTest` 완료, `AdminPagesTest`·`HardeningTest` 행에 이 Phase 화면과 명단 CSV 수식 방지 추가 |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 모델 | `ClassMeeting`(`scheduled()`, `held(as_of)`, `time_label`, `room_label`), `AttendanceRecord` | `ninefruits/attendance/models.py` |
| 열거형 | `AttendanceStatus`(출석·지각·결석·공결), `ClassMeetingStatus`(예정·휴강) | `attendance/enums.py` |
| Action | `GenerateClassMeetings`, `ManageClassMeetings`(추가·휴강·되돌리기·주제, `authorize`: 담당 교원 또는 범위 `sections.manage`), `RecordAttendance` | `attendance/actions/` |
| 서비스 | `AttendanceSummary`(진행 회차, 출석률 = (출석+지각+공결)/진행, 소수 첫째 자리 반올림), `SectionRoster`(명단, CSV, 조회 권한), `spreadsheet_cell` | `attendance/services/` |
| 정책 | 회차·출석 기록(변경은 Action으로만) | `attendance/policies.py` |
| 포털 | `/portal/sections/<id>/attendance/`(원본 `SectionAttendance`): 명단·회차 목록·회차 생성·추가·휴강·되돌리기, `?meeting=<id>` 출석 입력. 한 화면의 폼이 `action`을 POST하고 HTMX는 `#attendance` 블록을 교체한다(자바스크립트 없이도 동작). `/portal/attendance/`(원본 `MyAttendance`), 메뉴(학생·졸업생, 성적 다음) | `attendance/views/portal.py`, `templates/attendance/portal/` |
| 다운로드 | `/sections/<id>/roster.csv`, `/sections/<id>/attendance-sheet`(원본 `RosterCsvController`, `AttendanceSheetController`) | `attendance/views/downloads.py`, `templates/attendance/pdf/` |
| 관리 화면 | 개설강좌 수정 화면 **수업 회차** 탭(날짜, 시간, 강의실, 상태, 입력 수, 사유), 동작 버튼 **회차 생성**(확인 화면), 행 **휴강**(사유 화면)·**되돌리기**(확인 화면). `SectionClassMeetingsMixin`을 `SectionAdmin`에 섞었다 | `attendance/admin/__init__.py`, `offering/admin/sections.py` |
| 명령 | `attendance_generate_sessions {term} [--section=CSE2010-01] [--dry-run]`, 감사(학기, 강좌 수, 생성 회차 수) | `attendance/management/commands/` |
| 데모 시더 | `DemoAttendanceSeeder`: 이번 학기 회차 생성 후 진행 회차의 수강생 출석을 메모리에서 정해 5,000건 묶음 `bulk_create`. 상태 분포는 원본(85% 출석, 나머지 반 지각, 그다음 70% 결석, 나머지 공결)과 같고 옵션의 난수 생성기를 쓴다 | `setup/seeders/demo/attendance.py`, `demo.py` 목록 |
| 매뉴얼 | 관리자 25장, 운영 명령 레퍼런스. 4개 언어 | `docs/manual/*/` |
| 번역 | 앱 카탈로그 ko, zh_Hans, lo | `attendance/locale/` |

### 데모 시더 속도

원본 시더도 일괄 삽입(1,000건 묶음)이었지만 회차는 한 행씩 만들었다(`ClassMeeting::create`). 이식본은 강좌마다 회차를 한 번에 넣고, 출석 기록을 5,000건 묶음으로 넣는다. small에서 출석 시더 1.3초(회차 1,404개, 기록 3,820건), large에서 6.7초(회차 1,404개, 기록 23,355건, 이번 학기 수강 1,719건). 데모 강좌 수와 정원이 크기와 관계없이 같아(Phase 5) 기록 수는 크기에 따라 크게 늘지 않는다. `setup_demo --size=large --seed=42` 전체도 빈 DB에서 성공했다(다른 Phase 시더 포함). 행마다 감사 트리거(`audit.data_changes`)가 함께 쓰인다.

## 4. 계획과 달라진 점

| 항목 | 계획/원본 | 실제 | 이유 |
|---|---|---|---|
| 출석 입력 화면 | Livewire 상태(라디오, 비고, `markAll`, `prompt()`로 휴강 사유) | 한 폼 + 버튼별 `action`. **전원 출석**은 저장하지 않고 폼을 다시 그린다. 휴강 사유는 회차 행에서 펼치는 입력 칸. 실패하면 입력값과 오류를 그대로 다시 보여 준다 | Phase 5·6 포털과 같은 방식, 포털 CSP가 인라인 스크립트를 막는다 |
| 권한 오류 | 원본: 화면 안 메시지 "강좌 담당 교원과 관리 직원만…" | 같음(포털). 다운로드·관리 화면은 403 | 원본과 같음 |
| CSV 셀 규칙 위치 | 원본: `ReportCatalog::cell`(Phase 11 보고서) | `attendance.services.spreadsheet_cell`(같은 규칙, 같은 사례 테스트) | 보고서 앱은 Phase 11. Phase 11이 `ReportCatalog`를 만들 때 이 함수를 옮기거나 그대로 쓰면 된다 |
| 회차 생성 | 원본: 회차를 한 행씩 `create` | 강좌당 `bulk_create` 한 번(같은 날짜·시작 시간 검사는 메모리) | 데모·명령 속도. 결과는 같다 |
| 명단의 사진 | 원본: 행마다 `hasMedia` | 한 번의 쿼리로 사진이 있는 인물 집합 | N+1 방지 |
| 시간 입력 | 원본: 문자열 비교(`'09:00' >= '10:50'`) | `forms.TimeField`로 해석(잘못된 시간은 Django 메시지), 분 단위 | 형식이 틀린 입력이 DB 오류가 되지 않게 |
| 출석률 반올림 | PHP `round(x, 1)`(0.5는 0에서 먼 쪽) | `Decimal` `ROUND_HALF_UP`(예: 6.25 → 6.3) | Python `round`는 은행가 반올림이라 원본과 다르다 |
| 감사 `changes` 키 | 원본: 수강 ID(정수) | JSON으로 저장되어 문자열 키(`"14"`) | 원본도 JSON에서는 문자열 키다 |
| 교원 담당 강좌 열 이름 | 원본: `attendance.portal.title` | 같은 문구("수강생과 출석"), 링크는 "열기" | — |
| 개설강좌 화면 버그 수정 | Phase 4: `sections.view`만 있는 직원이 개설강좌 화면을 열면 500(`SectionForm.__init__`이 읽기 전용으로 빠진 `org_unit` 필드에 접근) | 필드가 있을 때만 설정(한 줄) | 원본은 조회 직원에게 수업 회차를 보여 준다. 이 Phase 테스트에서 발견 |
| 테스트의 직원 | 원본: `sections.manage`·`sections.view` 직원이 출석부를 받는다 | 같음. 단 RLS 아래에서 이 직원에게 명단이 비어 있어(수강·학적 조회 권한 없음) 출석부 내용은 담당 교원 요청으로 확인 | 원본 정책과 같다. 기본 역할(교무 담당, 학과 조교)은 `enrollments.view`와 `student_records.view`를 함께 가진다(매뉴얼 25장 마지막 절) |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| `ReportCatalog.cell` | 보고서 CSV가 같은 규칙을 써야 한다. `spreadsheet_cell`을 옮기거나 가져다 쓴다. `HardeningTest`의 CSV 사례는 그때 `tests/security/`에 | Phase 11 |
| `sections.manage`만 가진 역할 | RLS 아래 명단·출석부·입력 수가 비어 보이고, 출석 입력은 "수강하지 않는 학생"으로 거부된다(수강 행이 안 보임). 원본도 같다. 역할 화면에서 `enrollments.view`·`student_records.view`를 함께 주도록 안내 | 운영 안내(매뉴얼 2장 보완 검토) |
| 데모 시더 순서 | `DemoSeeder.SEEDERS`에서 출석은 원본처럼 강의평가·증명서·시험 뒤. 다른 Phase가 목록에 끼워 넣은 순서를 커밋 때 확인 | 조정 세션 |
| 결석 상한·지각 환산·출석 점수 반영, 공휴일 달력, 공결 신청 흐름, `.xlsx` | 원본도 구현하지 않음(ADR 0015 "하지 않은 것") | 요청 시 |
| LMS 연동 | 공지·과제·자료는 LMS | Phase 12 |

## 6. 실행 방법

`uv run manage.py setup_demo --size=small --force` 후(비밀번호 `demo-password`):

| 계정 | 볼 것 |
|---|---|
| `instructor@demo.test` | 포털 **담당 강좌 > 수강생과 출석 > 열기**: 명단과 출석 합계, 회차 목록(입력 수/수강생 수), 회차의 **출석 입력**, **전원 출석**, **휴강**, **회차 추가**, 명단(CSV), 출석부(PDF) |
| `student@demo.test` | 포털 **출석**: 과목별 합계와 회차별 기록 |
| `academic-affairs@demo.test` | 관리 화면 **교육과정과 개설 > 개설강좌 > 수정 > 수업 회차** 탭, **회차 생성** |

명령 예: `uv run manage.py attendance_generate_sessions 2026-FA --dry-run`, `uv run manage.py attendance_generate_sessions 2026-FA --section=CSE2010-01 --actor=academic-affairs@demo.test`.

## 7. 검증 결과

| 항목 | 결과 |
|---|---|
| 이 Phase 테스트(`tests/attendance/`) | 13개 통과 |
| 원본 오라클(`tests/Feature/Attendance/AttendanceTest.php`, DB `testing_p10`) | 5개 통과(90 단언) |
| 관련 테스트(`tests/db`, `tests/offering`, 수강신청 관리 화면, 성적표) | 통과(170개, 위 13개 포함) |
| 전체 테스트(`pytest -n 4 -m "not concurrency"`) | 937개 통과, 1개 실패(`tests/admin/test_reference_admin.py::test_searches_translated_names_in_every_language`, 단독 실행에서는 통과. 이 Phase와 무관, 다른 Phase가 동시에 카탈로그를 바꾸는 중) (139초) |
| 정적 검사 | ruff format/check(이 Phase 파일), `tools/checks/raw_sql.py`, `manage.py check` 통과. `makemigrations --check --dry-run` 변경 없음. mypy는 이 앱에 명령 `handle` 반환형 경고 1건(모든 명령 공통) |
| 데모 | 1절 |
