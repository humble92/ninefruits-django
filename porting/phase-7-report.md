# Phase 7 강의평가 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 7](porting-plan.md#phase-7-강의평가-m), 10절 "강의평가 익명성(ADR 0012)", 원본 [Phase 7 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-7-report.md), 원본 [ADR 0012](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0012-course-evaluation.md), [관리자 매뉴얼 22장](../docs/manual/ko/admin/22-course-evaluation.md)

## 1. 요약

강의평가 양식과 문항(번역 가능), 학기별 설정(`term_evaluations`, 최소 응답 수·응답률), 세션별 평가 기간(Phase 1 업무 기간 `course_evaluation`), 학생 익명 응답(완료 기록과 응답 분리, 응답 ID는 무작위 UUID, 순번·시각 없음, 감사 트리거 없음, 시스템 컨텍스트로 저장), 최소 기준을 둔 집계와 결과 공개, 교원 결과 화면, 학생 평가 포털, 독려 메일, 강의평가 설정 그룹과 화면, 명령 2개, 관리 화면 3개, Phase 6 성적 화면의 학기 가림 연결점 등록(평가 기간 중 미완료 학기의 성적과 성적표를 서버에서 가림), 표준 양식 프로파일 단계, 데모 시더(일괄 삽입), 관리자 매뉴얼 22장(4개 언어)을 구현했다.

- 이 Phase에서 추가한 테스트 22개(`tests/evaluation/`) 통과. 원본 테스트 3개 파일(사례 12개)을 모두 옮기고 10개를 더했다. 전체 결과는 7절.
- 데모: 빈 DB에서 `setup_install --force --profile=korean-university` 뒤 데모 시더를 차례로 실행(`--seed=42`). small에서 지난 학기 응답 215건(답변 3,284건, 의견 59건)과 결과 공개, 이번 학기 시연용 평가 기간. 원본 small(응답 209건, 답변 3,182건)과 같은 수준이다. 강의평가 시더 0.3초(small), 3.3초(medium, 응답 1,612건, 답변 24,582건).

## 2. 완료 기준

계획서 Phase 7 항목(원본 보고 2절과 같은 기준)

| 항목 | 결과 | 근거 |
|---|---|---|
| 양식/문항 | 충족 | 양식(척도 점수, 양끝 설명), 문항(영역, 척도·주관식, 필수, 역문항)을 관리 화면에서 관리. 응답이 있는 양식은 문항과 척도가 잠기고 **양식 복사**로 새 양식을 만든다(`test_evaluation_admin.py`) |
| 기간 | 충족 | 세션별 강의평가 업무 기간. 기간 밖 제출 거부(`test_evaluation.py`) |
| 익명 응답(완료와 응답 분리) | 충족 | 응답 표에는 `id`, `term_id`, `section_id`, `evaluation_form_id`만 있고 ID는 UUID v4. 응답·답변·완료는 `audit.record_changes`에 남지 않는다(`test_evaluation.py`). 학생은 DB에서 어떤 응답도 읽지 못하고 쓰지도 못하며, 교원은 공개 전 자기 강좌 응답도 읽지 못한다(`test_evaluation_access.py`) |
| 최소 응답 수 미만 비공개 집계 | 충족 | 공개 전, 최소 응답 수 미만, 최소 응답률 미만이면 응답 수만. 기준 이상에서 문항별 평균·분포(역문항 반전), 전체 평균, 의견(무작위 순서, 화면에서 이스케이프). 교원은 자기 강좌만(`test_evaluation.py`) |
| 미완료 시 성적 조회 제한(설정) | 충족 | 평가 기간 중 미완료 학기의 성적을 포털 성적 화면과 성적표에서 가림(Phase 6 `register_hidden_terms("evaluation", ...)`). 완료 후, 기간 종료 후, 설정을 끄면 보임(`test_evaluation.py`) |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `evaluation_remind`, `evaluation_publish_results` + `test_evaluation_admin.py` |
| 2. 매뉴얼 | 관리자 매뉴얼 22장 4개 언어(원본 장 + "이 설치본의 화면" 절), 21장의 Phase 7 예고 문구 정리, 운영 명령 레퍼런스 4개 언어(명령 2개) |
| 3. 시더, 팩토리, 데모 | 프로파일 `korean-university`의 Phase 7 단계(표준 양식: 5개 영역 × 3문항, 역문항 1개, 의견 1문항, 4개 언어, 멱등 테스트), 데모 `DemoEvaluationSeeder`(일괄 삽입), 팩토리 `tests/factories/evaluation.py`. 원본에 강의평가 필수 시더는 없다 |
| 4. `setup_install`, `setup_demo --size=small` | `setup_install` 성공. `setup_demo` 전체는 작성 시점에 병렬 작업 중인 Phase 8 증명서 데모 시더에서 멈췄다(5절). 강의평가까지의 데모 시더(+ Phase 9·10 시더)는 빈 DB에서 성공 |
| 5. 번역 | `ninefruits/evaluation/locale/` 85개 항목, `convert_translations.py --fill`로 원본 값 84개, 원본에 없는 문구 1개(`Already published.`)는 직접 번역. 이 앱의 `i18n_missing` 누락 0 |
| 6. 스키마 동등성 | 통과. 상태 전용 마이그레이션 `evaluation/0001_initial`. 스키마 변경 없음 |
| 7. 테스트 대응표 | `EvaluationTest`, `EvaluationAdminTest`, `EvaluationAccessTest` 완료, `AdminPagesTest` 행에 이 Phase 화면 추가 |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 모델 | `EvaluationForm`, `EvaluationQuestion`(번역 열 `TranslatableJSONField`), `TermEvaluation`(unique 제약 `term_evaluations_term_id_unique` 문서 선언), `EvaluationCompletion`(unique 제약 문서 선언), `EvaluationResponse`(`UUIDField(default=uuid4)`, 순번·시각·`created_at` 없음, 정렬 없음, `TimeStampedModel` 미사용), `EvaluationAnswer`(`CompositePrimaryKey("response_id", "question_id")`), 응답률 화면용 `SectionEvaluation`(개설강좌 프록시) | `ninefruits/evaluation/models/` |
| 범위 조회 | `EvaluationResponse.visible_to`(평가 권한 범위의 개설 조직, 공개된 학기의 자기 강좌). 6가지 사용자에서 RLS 결과와 같음(테스트). `SectionEvaluation.visible_to`(강의평가가 있는 학기, 평가 권한 범위) | `models/responses.py`, `models/section.py` |
| 열거형 | `QuestionType`(척도, 주관식) | `enums.py` |
| 서비스 | `EvaluationTasks`(평가할 수강: 수강 중·이수, `requires_evaluation`, 세션의 열린 평가 기간과 대상 조건, `pending`, `blocked_term_ids`), `EvaluationResults`(`can_view`, `for_section` → `SectionEvaluationResult`) | `services/` |
| Action | `SubmitEvaluation`(본인·기간·중복 확인 → 시스템 컨텍스트 한 트랜잭션에서 완료·응답·답변, unique 위반은 "이미 평가"), `ManageTermEvaluation`(`prepare`, `publish`, 감사 `evaluation.prepared`, `evaluation.published`), `CopyEvaluationForm`(감사 `evaluation_form.copied`) | `actions/` |
| 알림 | 독려 메일(받는 사람의 언어, 남은 과목 목록, 익명 안내, 포털 링크) | `notifications.py` |
| 정책 | 양식·문항·학기 강의평가: 원본 `EvaluationSetupPolicy`(조회 `reference_data.view`, 변경 `evaluations.manage`). 강좌별 응답: `evaluations.view` 또는 `evaluations.manage` | `policies.py` |
| 설정 | 그룹 `evaluations`(4개 값), 데이터 마이그레이션 `appsettings/0012_p7_evaluation_settings`(원본 기본값, 응답률 0), `0013_p7_raise_minimum_response_percent`(0이면 25, 되돌리면 25 → 0), 화면 **설정 > 강의평가** | `settings.py`, `settings_pages.py` |
| 관리 화면 | **학기 강의평가**(목록 위 **학기 강의평가 설정**, 행: **변경**·**결과 공개**, 응답 수 열), **강의평가 양식**(문항 탭, 응답이 있으면 읽기 전용·척도 잠금, 화면 위 **양식 복사**), **강좌별 응답**(학기·개설 조직 필터, 응답 수/대상 수, 응답률, 행: **결과**) | `admin/` |
| 포털 | `/portal/evaluations/`(평가할 과목, `?enrollment=`로 설문, HTMX `hx-confirm`, 실패 시 입력값 유지), `/portal/sections/<id>/evaluation/`(결과), 담당 강좌 표의 **강의평가 결과** 열, 성적 화면 안내와 링크, 메뉴(학생) | `views/portal.py`, `templates/evaluation/portal/` |
| 명령 | `evaluation_remind`(`--dry-run`), `evaluation_publish_results`(`--actor`가 공개한 사람) | `management/commands/` |
| 시더 | 프로파일 단계 `korean_university_evaluation.seed_evaluation_form`, 데모 `DemoEvaluationSeeder`(성적 데모 뒤) | `setup/seeders/` |
| RLS | DB 정책은 원본 그대로(`db/sql/policies/evaluations.sql`). 원본 `EvaluationAccessTest` 이식 | `tests/evaluation/test_evaluation_access.py` |
| 매뉴얼 | 관리자 22장, 운영 명령 레퍼런스, 21장 예고 문구. 4개 언어 | `docs/manual/*/` |

### 데모 시더 속도

원본은 완료·응답·답변을 하나씩 `create`했다. 이식본은 메모리에서 만들어 2,000행 묶음으로 일괄 삽입한다. 응답 ID는 데모 난수 생성기에서 뽑은 UUID v4라 `--seed`로 같은 데이터가 나온다(애플리케이션의 응답 ID는 `uuid4()`).

| 크기 | 지난 학기 이수 | 응답(완료) | 답변 | 강의평가 시더 |
|---|---|---|---|---|
| small | 305 | 215 | 3,284 | 0.3초 |
| medium | 2,320 | 1,612 | 24,582 | 3.3초 |

large는 지난 학기 강좌 정원이 medium과 같아(Phase 6 3절) 응답 수도 medium과 같은 수준이다.

## 4. 계획과 달라진 점

| 항목 | 계획/원본 | 실제 | 이유 |
|---|---|---|---|
| 양식 잠금·학기 양식 변경 판단 | 원본: 화면을 연 사용자의 DB 컨텍스트로 응답 존재 확인 | 시스템 컨텍스트에서 존재 여부만 확인(`responses_exist`) | RLS 아래 조직 범위 관리자는 다른 조직 강좌의 응답을 보지 못해, 쓰인 양식이 잠기지 않은 것처럼 보인다. 답은 참/거짓뿐이라 익명성에 영향이 없다 |
| 평가 기간 판정 | 원본: 수강마다 `isOpenInSession`(열린 기간 조회 반복) | 열린 강의평가 기간을 한 번 읽고 세션·대상 조건으로 거른다 | 결과는 같고 쿼리 수가 수강 수와 무관하다 |
| 설문 화면 | Livewire 상태(`enrollmentId`, `answers`), `wire:confirm` | 같은 URL 인수 `?enrollment=`, 한 폼 POST, `hx-confirm`, 실패는 입력값과 오류를 다시 보여 줌, 성공은 메시지를 세션에 담아 목록으로 | Phase 5·6 포털과 같은 방식. 자바스크립트 없이도 동작 |
| 관리 화면 동작 | Filament 모달(학기 설정·변경·공개·양식 복사) | 별도 입력·확인 화면(`run_form`) | 다른 Phase 관리 화면과 같은 방식 |
| 행 동작 표시 | 원본: 공개 안 된 행에만 **결과 공개** | 모든 행에 보이고, 이미 공개된 학기는 메시지 | unfold 행 동작은 행별로 숨길 수 없다(Phase 5·6과 같음) |
| 강좌별 응답의 **결과** | 원본: 새 탭 | 같은 창에서 포털 결과 화면 | unfold 행 동작은 새 탭 옵션이 없다 |
| 평균 반올림 | PHP `round`(0.5 올림) | `Decimal` `ROUND_HALF_UP` | 같은 값(파이썬 `round`는 은행가 반올림이라 쓰지 않음) |
| 의견 순서 | `shuffle` | `random.SystemRandom().shuffle` | 순서로 학생을 짐작할 수 없게 예측 불가능한 난수 |
| 학기 강의평가 변경 화면 | 원본: 학기 칸 비활성 | 같음. 비운 최소 기준은 기존 값 유지(원본 `prepare`) | — |
| 표준 양식 단계 | 원본 프로파일 시더 안 메서드 | 공용 프로파일의 `LATER_PHASE_STEPS`에 한 줄 등록, 내용은 별도 모듈 | Phase 1이 둔 연결점 |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| `setup_demo` 전체 실행 | 작성 시점에 Phase 8 증명서 데모 시더가 `Media path is already taken`으로 실패해 데모 전체가 끝나지 않았다(강의평가 시더는 그 앞에서 끝남). 병렬 작업 중인 영역이라 손대지 않았다 | Phase 8 |
| 다른 앱의 검사 | 전체 테스트의 `test_command_documentation`(Phase 9 `assessment_*` 명령 미문서), `i18n_missing --strict`(Phase 9 등 다른 앱 카탈로그 누락), `makemigrations --check`(Phase 8 `certificate`)가 작성 시점에 다른 Phase 작업 때문에 실패한다. 이 Phase 영역은 모두 통과 | 각 Phase |
| 교원·학과별 강의평가 통계 보고서 | 원본도 Phase 11 | Phase 11 |
| 과목 유형별 양식, 레거시 응답 이관 | 원본도 하지 않음(이관 시 완료 기록과 익명 응답으로 나눠 넣는다) | 수요 확인 후, 데이터 이관 때 |
| DB 물리 저장 순서 | ADR 0012의 남는 한계(입력 순서대로 저장될 수 있음). DB 관리자 수준 접근이 필요하다 | 운영 안내 |
| 스케줄 작업 문서 | `evaluation_remind`의 스케줄 등록 안내는 `scheduled-jobs.md`(Phase 13) | Phase 13 |

## 6. 실행 방법

`uv run manage.py setup_demo --size=small` 후(비밀번호 `demo-password`):

| 계정 | 볼 것 |
|---|---|
| `instructor@demo.test` | 포털 **담당 강좌**에서 지난 학기를 고르면 **강의평가 결과** 열의 **결과**(공개됨, 응답 3건 이상인 강좌는 문항별 평균·분포·의견) |
| `academic-affairs@demo.test` | **강의평가 > 학기 강의평가**(지난 학기 공개, 이번 학기 진행 중), **강의평가 양식**(표준 양식, 응답이 있어 잠김, **양식 복사**), **강좌별 응답**, **설정 > 강의평가** |
| 이번 학기 수강 학생(예: `student@demo.test`) | 포털 **강의평가**(시연용 평가 기간이 열려 있음). 성적 조회 제한은 확정 성적이 있는 학기에서 보이므로 테스트(`test_evaluation.py`)로 확인한다 |

명령 예: `uv run manage.py evaluation_remind 2026-FA --dry-run`, `uv run manage.py evaluation_publish_results 2026-SP --actor=academic-affairs@demo.test`.

## 7. 검증 결과

| 항목 | 결과 |
|---|---|
| 이 Phase 테스트(`tests/evaluation/`) | 22개 통과(30초, 그중 tiny 데모를 시딩하는 테스트 3개가 14초) |
| 관련 영역(`tests/evaluation`, `grading`, `db`, `tooling`, `offering`, `setup`, `i18n`, `portal`) | 385개 통과, 4개 실패(`test_command_documentation`의 Phase 9 명령, 5절) |
| 전체 테스트(`pytest -n 4 -m "not concurrency"`) | 932개 통과, 6개 실패(152초). 실패는 모두 작성 시점에 진행 중인 Phase 9 영역: `tests/assessment/test_assessment_admin.py` 2개, `test_command_documentation` 4개(`assessment_*` 명령 미문서) |
| 원본 테스트(오라클, `laravel-test testing_p7`) | `EvaluationTest` 7개, `EvaluationAdminTest` 3개, `EvaluationAccessTest` 2개 통과(원본 동작 확인) |
| 정적 검사 | ruff format/check(이 Phase 파일), `tools/checks/raw_sql.py`, `manage.py check`, `naming_check` 통과. `makemigrations --check`는 이 앱 변경 없음(Phase 8 `certificate`만 남음) |
| 데모 | 3절 표 |
