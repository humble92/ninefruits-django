# 9. CSV 가져오기

조직 단위, 프로그램, 건물, 강의실, 코드 데이터 목록 화면 위쪽 **CSV 가져오기** 버튼을 쓴다(`기준정보 CSV 가져오기` 권한). 학적, 교원, 교과목, 수강신청 제한 가져오기는 해당 Phase에서 같은 방식으로 추가된다. 아주 큰 파일은 IT 운영자가 `reference_import` 명령으로 같은 방식으로 가져올 수 있다.

## 공통 규칙

- 첫 줄은 열 이름(아래 표). 인코딩은 UTF-8. 엑셀에서는 "CSV UTF-8"로 저장한다.
- 같은 코드의 행이 이미 있으면 **갱신**한다. 같은 파일을 다시 가져와도 중복되지 않는다.
- 언어별 열은 `열이름_언어` 형식이다: `name_en`, `name_ko`, `name_zh-hans`. 새 행은 영어 이름(`name_en`)이 필수다. 빈 칸은 기존 번역을 지우지 않는다.
- 날짜는 `2026-03-01`, 예/아니오는 `1`/`0` 또는 `true`/`false`.
- 파일을 올리면 머리글을 먼저 검사한다(필수 열이 없으면 아무것도 가져오지 않는다). 행이 500개 이하이면 바로 가져오고, 더 많으면 백그라운드(Celery)로 처리한다. 결과는 **기준정보 > CSV 가져오기 기록**의 가져오기 화면에 나온다(가져온 행 수, 실패한 행과 사유). 실패한 행이 있으면 **실패한 행 내려받기**로 사유가 적힌 CSV를 받는다. 고쳐서 그 파일만 다시 가져오면 된다.
- 열 이름은 아래 표와 같아야 한다. 모르는 열은 무시한다. 원본 시스템의 `name_zh_CN` 열 이름도 `name_zh-hans`로 받아들인다.

## 열 형식

| 종류 | 필수 열 | 선택 열 |
|---|---|---|
| 조직 단위 | `code`, `type`(조직 단위 유형 코드), `name_en`, `effective_start_date` | `parent`(상위 코드), `name_ko` 등, `short_name_*`, `effective_end_date`, `sort_order` |
| 프로그램 | `code`, `org_unit`(조직 코드), `degree_level`, `name_en`, `effective_start_date` | `degree_title_*`, `standard_duration_years`, `effective_end_date`, `allows_second_major`, `allows_minor` |
| 건물 | `code`, `name_en` | `name_*`, `address`, `is_active` |
| 강의실 | `building`(건물 코드), `code`(호실) | `name_*`, `room_type`(용도 코드), `org_unit`, `capacity`, `is_schedulable`, `is_active` |
| 코드 값 | `type`(목록 코드), `code`, `name_en` | `name_*`, `sort_order`, `is_active` |

`degree_level` 값: `associate`, `bachelor`, `master`, `doctorate`, `certificate`, `non_degree`

조직 단위는 상위 조직이 먼저 나와야 한다(대학교 → 단과대학 → 학과 순으로 정렬).

## 예시: 조직 단위

```csv
code,type,parent,name_en,name_ko,effective_start_date
UNI,university,,Sample University,샘플대학교,1990-03-01
ENG,college,UNI,College of Engineering,공과대학,1990-03-01
CSE,department,ENG,Computer Science,컴퓨터공학과,1995-03-01
```

## 학생과 교원

학적은 `student_number`(학번), 교원은 `employee_number`(교직원 번호)로 기존 행을 찾아 갱신한다. 두 종류 모두 인물 열을 함께 쓴다.

| 종류 | 새 행 필수 열 | 선택 열 |
|---|---|---|
| 학적 | `student_number`, `program`(프로그램 코드), `admission_date`, `family_name` | `catalog_year`(비면 입학 연도), `year_level`, `status`, `graduation_date`, `institutional_email` |
| 교원 | `employee_number`, `org_unit`(조직 코드), `employment_type`, `family_name` | `academic_title_*`, `hire_date`, `end_date` |
| 인물 열(공통) | — | `given_name`, `name_ko` 등 언어별 이름, `birth_date`, `gender`, `email`, `phone`, `national_id` |

- `status` 값: `enrolled`, `on_leave`, `withdrawn`, `dismissed`, `graduated`(졸업이면 `graduation_date` 필수). 가져오기로 바꾼 상태는 **자료 정정**으로 취급해 학적 변동 이력을 만들지 않는다. 실제 변동은 화면에서 처리한다([13장](13-status-changes-and-advisors.md)).
- `employment_type` 값: `full_time`, `part_time`, `adjunct`, `visiting`, `emeritus`. `gender` 값: `female`, `male`, `other`, `undisclosed`.
- 새 학적의 `national_id`가 기존 인물과 같으면 그 인물에 학적을 붙인다(재입학). 그 밖에는 새 인물을 만든다. 갱신할 때 빈 칸은 기존 값을 지우지 않는다.
- 가져온 학생, 교원은 계정이 없다. [계정 초대](14-merge-and-invitations.md#계정-초대)로 가입 안내를 보낸다.

```csv
student_number,program,admission_date,year_level,status,family_name,given_name,name_ko,birth_date
202600001,B-CSE,2026-03-02,1,enrolled,Kim,Minsu,김민수,2007-05-01
```

교과목(Phase 4) 가져오기는 해당 기능과 함께 추가된다.
