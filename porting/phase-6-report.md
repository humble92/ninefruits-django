# Phase 6 성적 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 6](porting-plan.md#phase-6-성적-l), 10절 "평점 계산"·"학기 마감 배치", 13.1절, 원본 [Phase 6 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-6-report.md), 원본 [ADR 0011](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0011-grades-and-term-records.md), [관리자 매뉴얼 21장](../docs/manual/ko/admin/21-grades.md)

## 1. 요약

교원 포털 성적 입력(절대평가 점수 → 성적 즉시 표시, 상대평가 성적만, 임시 저장·제출), 직원의 확정·반려, 확정 성적 정정 요청과 승인(직무 분리), 평가 방식 변경 요청과 승인, 상대평가 등급 비율 상한과 직원 예외 제출, 평점 계산(정수 연산, 자릿수·반올림·재수강 정책), 학기 기록, 학기 마감(Celery chord, `job_batches` 진행률, 재시도, 완료 메일)과 학업 상태·학사경고·제적 검토·성적우수, 학생 성적 조회와 성적표(인쇄용 HTML + Gotenberg PDF), 성적 조회 제한(수강신청 제한의 `blocks_grades`, Phase 7 강의평가용 학기 가림 연결점), 성적 처리 정책 설정 그룹·화면, 알림 4종(+ 학기 마감 완료 메일), 명령 3개, 관리 화면 4개와 학적 화면의 성적표 버튼, 데모 성적 시더 2개(일괄 삽입), 관리자 매뉴얼 21장(4개 언어)을 구현했다. Phase 5가 남긴 수강 행의 성적 열을 모두 쓰고, `GradeStatus`는 `grading.enums`로 옮겼다(`registration.enums`에는 별칭).

- 이 Phase에서 추가한 테스트 82개(`tests/grading/`) 통과. 원본 테스트 8개 파일의 사례를 모두 옮겼다. 전체 결과는 7절.
- 빈 DB에서 `setup_install --force --profile=korean-university`(2.4초)와 `setup_demo --size=small --seed=42`(8.2초, 데모 전체) 성공. 지난 학기 확정 성적 305건, 학기 기록 61건(학사경고 6명, 성적우수 6명), 이번 학기 제출 완료 6건·임시 저장 3건, 재수강 37건, 대기 중인 정정 요청 1건, 상대평가 강좌 17개. 원본 small(확정 305건, 학기 기록 61건, 학사경고 5명, 성적우수 4명, 재수강 33건)과 같은 수준이다.

## 2. 완료 기준

| 완료 기준 | 결과 | 근거 |
|---|---|---|
| 평점 계산 경계값 테스트 | 충족 | `tests/grading/test_gpa_calculator.py`(16개): 반올림·버림, 0·2·3자리, 정확한 반올림 경계(3.4375 → 3.438), 4.3 척도 합(3.000), 순환소수, 0.5학점, F 포함, P/F만(평점 없음), 빈 집합, 신청·취득·평점 학점, 재수강 최근/최고(연쇄 재수강), 학기 평점은 모든 성적 유지. 학점 ×10, 평점 ×100 정수로 계산하고 `Decimal`로 돌려준다(부동소수점 없음) |
| 확정 성적의 직접 수정이 애플리케이션과 DB 양쪽에서 차단 | 충족 | DB: `test_finalized_grade_guard.py`(9개). 성적·이수·상태·학점·초안 되돌리기·삭제를 `util.guard_finalized_grade`가 거부, 대기 요청·다른 수강의 승인 요청·적용된 요청으로는 열리지 않음, 본인 요청 승인은 `grade_change_requests_second_person_check`가 거부. 애플리케이션: `test_grade_workflow.py`(제출 후 교원 수정 거부, 확정 전 정정 요청 거부, 본인 요청 승인 거부, 관계없는 사용자 거부). RLS: `test_grade_access.py`(교원은 자기 강좌의 미제출 성적만 쓰고 확정할 수 없으며 다른 강좌에 정정 요청 불가) |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `term_close`, `grades_recalculate`, `grades_remind_missing` + `test_grading_commands.py` |
| 2. 매뉴얼 | 관리자 매뉴얼 21장 4개 언어(원본 장 + "이 설치본의 화면" 절), 20장의 Phase 6 예고 문구 정리, 운영 명령 레퍼런스 4개 언어(명령 3개) |
| 3. 시더, 팩토리, 데모 | 프로파일 `yust-legacy`의 Phase 6 단계(레거시 성적 정책, 멱등 테스트), 데모 `DemoGradeHistorySeeder`·`DemoGradingSeeder`(일괄 삽입). 팩토리는 Phase 5의 `EnrollmentFactory(grade=...)`(4.5 척도 자동 생성)와 4.5 척도 시더를 그대로 쓴다. 원본에 성적 필수 시더는 없다 |
| 4. `setup_install`, `setup_demo --size=small` | 빈 DB에서 성공 |
| 5. 번역 | `ninefruits/grading/locale/` 228개 항목, `convert_translations.py --fill`로 원본 값 채움(원본에 없는 문구 13개는 직접 번역). `i18n_missing --strict` 통과 |
| 6. 스키마 동등성 | 통과. 상태 전용 마이그레이션 `grading/0002_p6_grades`, `core/0050_job_batches_state`(기존 `job_batches` 표의 모델 상태). 스키마 변경 없음 |
| 7. 테스트 대응표 | `GpaCalculatorTest`, `GradeWorkflowTest`, `GradingCommandsTest`, `RelativeEvaluationTest`, `TermCloseTest`, `FinalizedGradeGuardTest`, `GradeAccessTest`, `GradingAdminTest` 완료, `AdminPagesTest` 행에 이 Phase 화면 추가 |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 모델 | `TermRecord`(평점 열은 자릿수 없는 `numeric`, 계산한 자릿수 그대로 저장), `GradeChangeRequest`, `EvaluationMethodRequest`, 성적 처리 현황용 `SectionGrade`(개설강좌 프록시), `core.JobBatch`(원본 `job_batches` 표). 부분 unique 인덱스 2개와 unique 제약 1개는 같은 이름으로 `Meta`에 문서로 선언 | `ninefruits/grading/models/`, `ninefruits/core/batches.py` |
| 범위 조회 | `TermRecord.visible_to`(볼 수 있는 학적, 전역 `grades.manage`는 전부), `GradeChangeRequest.visible_to`(볼 수 있는 수강) + `in_scope_of`(관리 화면: 본인 요청과 승인·요청·조회 범위 강좌), `EvaluationMethodRequest.visible_to`(편성 범위 강좌와 본인 요청, 표에 RLS 없음), `SectionGrade.visible_to`. 9가지 사용자 × 2개 표에서 RLS 결과와 같음(테스트) | `models/`, `tests/grading/test_grade_access.py` |
| 열거형 | `GradeStatus`(이동), `GradeAppliesTo`, `EvaluationMethod`, `AcademicStanding`, `GpaRounding`, `RetakePolicy`, `GradeChangeStatus`, `RequestStatus` | `grading/enums.py` |
| 서비스 | `GpaCalculator`, `GradeDistributionCheck`, `GradeOptions`(점수 → 성적, P/F, 재수강 상한), `TermRecordCalculator`(여러 학생을 한 번에: 성적 조회 1회 + upsert 1회), `AcademicStandingJudge`, `GradeReport`, 학기 가림 연결점 `register_hidden_terms` | `grading/services/` |
| Action | `SaveGrades`(임시 저장·제출·예외 제출·검토자 메일·제출 성적 직원 수정 감사), `FinalizeGrades`(확정·반려), `ManageGradeChanges`(요청·승인·반려·취소, 승인 시 `app.grade_change_request_id`), `ManageEvaluationMethodRequests`, `RecalculateTermRecords`, `CloseTerm`(사전 점검, 시작, 묶음 처리, 마무리), `SaveGradeScale`(Phase 1) | `grading/actions/` |
| 학기 마감 배치 | `CloseTerm.close`가 `job_batches` 행을 만들고 커밋 뒤 chord 실행: 학생 100명 묶음마다 `grading.close_term_records`(DB 오류 3회 재시도, 지수 대기) → `grading.finish_term_close`(성적우수 순위, 기록 마감, 학기 상태, 감사 `term.closed`, `TermClosed` 이벤트, 시작한 직원에게 메일). 실패한 묶음은 배치에 실패로 남고 마무리는 실행되지 않는다. 진행률은 학기 기록 목록 위에 표시 | `actions/close_term.py`, `tasks.py` |
| 이벤트 | `GradesFinalized`(LMS는 Phase 12), `TermClosed` | `events.py` |
| 알림 | 반려(교원), 미제출 안내(교원), 평가 방식 결정(교원), 예외 제출(검토 권한자, 조직 범위), 학기 마감 완료(시작한 직원). 받는 사람의 언어로 | `notifications.py` |
| 정책 | 학기 기록·정정 요청·평가 방식 요청·성적 처리 현황(모두 읽기 전용, 변경은 Action으로) | `policies.py` |
| 설정 | 그룹 `grading`(14개 값), 데이터 마이그레이션 `appsettings/0010_p6_grading_settings`, `0011_p6_relative_grade_caps`(원본 두 파일), 화면 **설정 > 성적 처리 정책**(척도 표시, 평점, 상대평가 상한, 학업 상태, 성적우수) | `grading/settings.py`, `settings_pages.py` |
| 관리 화면 | 성적 처리 현황(학기·개설 조직·예외 제출·확정 가능 필터, 행: 성적·확정·반려, 선택 강좌 확정), 평가 방식 변경 요청·성적 정정(대기 기본 필터, 메뉴에 대기 건수, 승인·반려·요청 취소), 학기 기록(학기·학업 상태·성적우수·프로그램 필터, 행: 성적표, 목록 위: 학기 마감·재계산, 진행 중인 마감 진행률), 학적 화면 **성적표** 버튼 | `grading/admin/`, `person/admin/student_records.py` |
| 포털 | `/portal/sections/<id>/grades/` 성적 입력(HTMX: 점수별 성적 미리 보기 partial, 블록 교체, 자바스크립트 없이도 동작), `/portal/grades/` 성적(졸업생 포함), `/portal/grades/transcript/` 성적표(HTML, `?format=pdf`), 담당 강좌 화면의 **성적 입력** 열, 메뉴(학생·졸업생) | `grading/views/portal.py`, `templates/grading/` |
| 성적표 | 직원용 `/student-records/<id>/transcript/`(볼 수 있는 학적 + `grades.view`, 감사 `transcript.viewed`), 같은 템플릿을 Gotenberg로 PDF | `grading/views/transcript.py` |
| 명령 | `term_close`(종료 코드 2), `grades_recalculate`(사유 필수), `grades_remind_missing`(`--dry-run`) | `grading/management/commands/` |
| 시더 | 프로파일 단계 `yust_legacy_grading.seed_grading_policy`, 데모 `DemoGradeHistorySeeder`(수강신청 데모 앞), `DemoGradingSeeder`(뒤) | `setup/seeders/` |
| 매뉴얼 | 관리자 21장, 운영 명령 레퍼런스. 4개 언어 | `docs/manual/*/` |

### 데모 시더 속도

원본 성적 이력 시더는 수강 행을 하나씩 팩토리로 만들고 학생마다 학기 기록을 계산했다. 이식본은 지난 학기 수강을 메모리에서 정해(정원, 같은 과목, 수강 대상) 일괄 삽입하고, 학기 기록·학업 상태·성적우수를 500명 묶음으로 계산한다(`CloseTerm.close_records`). 이번 학기 성적 입력, 정정 요청은 원본처럼 Action을 거친다. 같은 기계, 빈 DB에서 `setup_install` 뒤 시더를 순서대로 실행해 잰 값(`--seed=42`):

| 크기 | 학적 | 지난 학기 확정 성적 | 학기 기록 | 성적 이력 시더 | 성적 입력 시더 | 데모 시더 전체 |
|---|---|---|---|---|---|---|
| small | 104 | 305 | 61 | 1.1초 | 0.3초 | 5.0초 |
| medium | 2,004 | 2,320 | 471 | 2.9초 | 1.6초 | 13.7초 |
| large | 20,004 | 2,320 | 474 | 3.2초 | 1.7초 | 60.3초 |

medium 이상에서 성적 수가 같은 것은 지난 학기 강좌(52개, 이번 학기에서 복사)의 정원이 크기와 관계없이 같기 때문이다(Phase 5 수강신청과 같은 편성 규칙). large 시간의 대부분은 인물(15.7초)과 수강신청 시도 기록(33.5초)이다. `setup_demo` 명령 전체(프로세스 시작 포함)는 small 8.2초.

## 4. 계획과 달라진 점

| 항목 | 계획/원본 | 실제 | 이유 |
|---|---|---|---|
| 학기 마감 배치 | 원본 `Bus::batch` + 체인, Horizon에서 진행 확인 | Celery chord(`group` → 마무리), 진행률은 원본 표 `job_batches`(`core.JobBatch`), DB 오류 3회 재시도, 실패 묶음은 배치에 기록, 완료 메일 | 계획 10절, 13.1절. 원본 표를 그대로 써서 스키마가 같다 |
| 마감 묶음 | 계획: 학생 단위 작업 | 원본처럼 100명 묶음, 묶음 안은 일괄 계산 | 작업 수와 쿼리 수를 줄인다. 묶음은 다시 실행해도 결과가 같다 |
| 학기 기록 쓰기 | 원본: 요청 사용자 DB 컨텍스트 | 계산(확정·정정 승인·재계산·마감 뒤)은 권한 확인 뒤 시스템 컨텍스트에서 쓴다 | RLS `term_records_staff_all`은 전역 `grades.manage`만 쓰기를 허용한다. 조직 범위 학적 담당이 확정하면 원본에서는 학기 기록 쓰기가 DB에서 거부된다. 파생 데이터이므로 시스템으로 쓴다 |
| 정정 승인의 잠금 | 원본: 수강 행을 관계와 함께 읽어 잠금 | 수강 행만 잠그고 읽는다(학적·학기는 따로) | RLS 아래 승인자가 학적을 못 보면 조인 결과가 비어 승인이 실패한다(테스트에서 발견) |
| 성적표 | 원본: 인쇄용 HTML(인쇄 버튼은 `window.print`) | 같은 HTML + `?format=pdf`(Gotenberg). 인쇄 버튼은 없앰(브라우저 인쇄) | 작업 지시(PDF). 포털 CSP가 인라인 스크립트를 막는다. 공식 성적증명서는 Phase 8 |
| 성적 입력 화면 | Livewire 상태(입력 중 값, 메시지) | 한 폼 + 버튼별 `action`. 성공은 메시지를 세션에 담아 되돌아가고, 실패는 입력값과 오류를 그대로 다시 보여 준다. 점수 미리 보기는 HTMX GET partial. 정정 요청 칸은 표 아래에 열린다 | Phase 5 포털과 같은 방식. 자바스크립트 없이 동작 |
| LMS 점수 불러오기 | 원본: 성적 입력 화면 버튼 | 없음 | LMS는 Phase 12 |
| 강의평가 미완료 학기 가림 | 원본: `EvaluationTasks::blockedTermIds` | 연결점 `register_hidden_terms(key, terms, notice=, link=)`. 성적 화면·성적표·최근 기록이 따른다(테스트) | Phase 7이 완료 데이터를 제공한다 |
| 등급 비율 상한 입력 | 원본: 반복 입력(등급군, 상한) | 한 칸에 `A=30, B=40` | unfold에 반복 입력 위젯이 없다. 검증(글자 하나, 0~100) 같음 |
| 행 동작 표시 | 원본: 제출 건이 있는 행에만 확정·반려, 처리할 수 있는 요청에만 승인·반려 | 모든 행에 보이고 실행 화면에서 확인(권한 없으면 403, 대상이 아니면 오류 메시지) | unfold 행 동작 권한은 행별로 판정되지 않는다(Phase 5와 같음) |
| 메뉴 대기 건수 | 원본: Filament 배지 | `navigation_badge(request)`를 둔 관리 화면은 메뉴에 배지(공용 `adminpanel/navigation.py`에 추가) | 원본과 같은 표시 |
| `GradeStatus` 위치 | Phase 5: `registration.enums` | `grading.enums`, `registration.enums.GradeStatus`는 별칭 | 작업 지시. 라벨(msgid·문맥)은 그대로 |
| 설정 값 `None` | 원본: JSON `null` | `SettingsGroup.save`와 `add_settings`가 `None`을 JSON `null`(`JSONNull()`)로 쓴다(공용 `settings/groups/base.py`) | `retake_max_grade`가 처음으로 `null`이 기본값인 설정이라 `payload NOT NULL` 위반이 드러났다 |
| 데모 지난 학기 강좌 | 원본 small: 99개(지난 학기) | 52개(이번 학기에서 복사) | 원본도 이번 학기를 복사하는데 다른 Phase 시더가 강좌를 더한 결과로 보인다. 성적·학기 기록 수는 원본과 같은 수준 |
| 테스트의 실행 컨텍스트 | 원본: Action을 테스트 기본 컨텍스트로 호출 | 워크플로 테스트는 Action을 요청처럼 사용자 DB 컨텍스트(`as_user`)로 실행. 학적 담당 픽스처에 `grades.view`를 더함 | RLS 아래에서도 흐름이 되는지 확인. `grades.manage`만 가진 사용자는 RLS 아래 수강 행을 읽지 못한다(역할 기본값은 항상 함께 준다) |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| 강의평가 미완료 학기 가림 | `register_hidden_terms("evaluation", ...)` 등록, 안내 문구와 링크 | Phase 7 |
| 공식 성적증명서, 증명서 발급 제한 | `blocks_certificates` 적용 | Phase 8 |
| LMS 점수 불러오기, `GradesFinalized` 리스너 | 성적 입력 화면 버튼, 동기화 작업 | Phase 12 |
| 성적 보고용 `reporting` 뷰 | 원본 Phase 11 | Phase 11 |
| `grades.manage`만 가진 역할 | RLS 아래 수강 행 조회에 `grades.view`(또는 수강 조회 권한)가 필요하다. 역할 화면에서 하나만 주면 성적 처리 현황이 비어 보인다. 원본도 같다 | 운영 안내(매뉴얼 2장 보완 검토) |
| 다른 앱의 `gettext as gettext_now` | `makemessages`가 이 이름을 추출하지 않아 해당 문구가 카탈로그에 없다(예: 수강신청 관리 화면의 일부 메시지). 성적 앱은 `gettext`로 바꿨다 | 해당 앱 담당(Phase 13 번역 점검 전) |
| unfold 경고 | 일괄 동작이 있는 목록에서 unfold의 `get_action_choices` 서명 경고(Django 2028 제거 예정) | unfold 업데이트 시 |
| 스케줄 작업 문서 | `docs/manual/*/operations/scheduled-jobs.md`는 Phase 13 작성 예정. 학기 마감 작업은 명령 레퍼런스에 적었다 | Phase 13 |
| I 성적 기한 후 자동 F, 학과별 성적우수 비율, 학생 이의 신청 | 원본도 미구현 | 요청 시 |

## 6. 실행 방법

`uv run manage.py setup_demo --size=small` 후(비밀번호 `demo-password`):

| 계정 | 볼 것 |
|---|---|
| `instructor@demo.test` | 포털 **담당 강좌 > 성적 입력**: 이번 학기 강좌(시연용 성적 입력 기간이 열려 있음, 강좌 셋 중 하나는 상대평가). 절대평가는 점수를 넣으면 잠시 뒤 성적이 보이고, 상대평가는 성적만 고르고 **등급 비율 검사**. 지난 학기 강좌에는 대기 중인 정정 요청이 하나 있다 |
| `registrar@demo.test` | 관리 화면 **성적 > 성적 처리 현황**(확정 가능 필터, 확정·반려), **성적 정정**(대기 1건 승인), **학기 기록**(지난 학기 학사경고·성적우수 명단, 학기 마감 미리 보기) |
| `academic-affairs@demo.test` | **설정 > 성적 처리 정책**, **성적 > 평가 방식 변경 요청** |
| `student@demo.test` | 포털 **성적**과 성적표(인쇄, PDF) |

명령 예: `uv run manage.py term_close 2026-FA --dry-run`, `uv run manage.py grades_remind_missing 2026-FA --dry-run`, `uv run manage.py grades_recalculate --term=2026-SP --reason="정책 변경"`.

## 7. 검증 결과

| 항목 | 결과 |
|---|---|
| 전체 테스트(`pytest -n 4 -m "not concurrency"`) | 818개 통과(63초) |
| 동시성 테스트(`pytest -m concurrency`) | 1개 통과(12초) |
| 이 Phase 테스트(`tests/grading/`) | 82개 통과(40초, 그중 tiny 데모를 시딩하는 관리 화면 테스트 6개가 21초) |
| 정적 검사 | ruff format/check, `tools/checks/raw_sql.py`, `manage.py check`, `makemigrations --check --dry-run`, `naming_check`, `i18n_missing --strict` 통과 |
| 데모 | 3절 표 |
