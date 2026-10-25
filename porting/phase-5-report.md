# Phase 5 수강신청 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 5](porting-plan.md#phase-5-수강신청-l), 10절 "좌석 확보", 13.1절, 원본 [Phase 5 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-5-report.md), 원본 [ADR 0010](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0010-registration.md), [관리자 매뉴얼 20장](../docs/manual/ko/admin/20-registration.md)

## 1. 요약

학기별 규칙 세트와 규칙 10종, 규칙 엔진, 규칙 카탈로그 시더, 수강신청 제한(hold)과 규칙 예외(override), 제한 CSV 가져오기, 학점 상한 정책, 장바구니, 시차 오픈(Phase 1 업무 기간과 `TermResolver`), 좌석 할당(유보석)과 전환 작업, 대기자 자동 승격(이벤트 → 커밋 뒤 Celery 작업, 강좌별 Redis 잠금, 메일), 포털 수강신청·취소·철회와 학생 시간표(HTMX), 직원 수강 조정, 수강신청 기록, 명령 4개, 관리 화면 7개와 개설강좌 화면의 수강생·대기자 탭, 데모 수강신청(일괄 삽입), 관리자 매뉴얼 20장(4개 언어)을 구현했다. Phase 4가 미뤄 둔 `UpdateSection`의 평가 방식 변경 제한(성적이 입력된 수강이 있으면 거부)은 수강 모델이 생기면서 그대로 동작하고 테스트로 고정했다.

- 이 Phase에서 추가한 테스트 61개(`tests/registration/`, 동시성 1개 포함) 통과. 전체 결과는 7절. ruff format/check, raw SQL 검사, `manage.py check`, `makemigrations --check`, `naming_check`, `i18n_missing --strict`(ko, zh_Hans, lo), 스키마 동등성·모델 열 일치 검사 통과.
- 빈 DB에서 `setup_install --force --profile=korean-university`(2.6초), `setup_demo --size=small --seed=42`(5.2초, 데모 전체), `--size=large`(58.6초, 원본 65분) 성공. 데모 수강 272건, 시도 기록 523건(원본 small: 이번 학기 수강 약 270건, 시도 515건). 모든 강좌의 신청 인원 카운터가 수강 행 수와 같고 정원 초과 0건.

## 2. 완료 기준

| 완료 기준 | 결과 | 근거 |
|---|---|---|
| 레거시 샘플 규칙을 설정만으로 재현 (원본 3.4절 버그는 재현하지 않음) | 충족 | `tests/registration/test_legacy_rules.py`(10개): `yust-legacy` 프로파일이 넣은 학점 상한 7종(학기 종류별 행)으로 입학 연도·간호학부 여부·학기 종류 8가지 조합의 상한을 확인. 14학번 이후 간호학부는 21학점(18+3 신청 성공, 다음 3학점 거절). 학점은행 과목(`009%`, `900%`)은 상한 계산에서 제외. 수강 대상·학과·입학 연도, 선수과목, 시간 중복, 정원, 같은 과목 중복, 재수강 표시, 수강신청 제한, 규칙 예외를 기본 규칙 세트로 재현. 코드 변경 없이 설정 행만으로 재현 |
| 동시 요청에서도 정원 초과 없음 | 충족 | `tests/registration/test_concurrent_registration.py`(`-m concurrency`): `multiprocessing`(`spawn`) 프로세스 16개가 각자 DB 연결로 정원 5인 강좌에 같은 순간 신청 → 정확히 5명 신청, 11명은 정원 마감 거절, 카운터와 수강 행 모두 5. 강좌 행 잠금(`select_for_update`)을 빼면 이 테스트가 실패하는 것을 확인(카운터 CHECK 위반 오류). 픽스처는 커밋하고 끝에 스키마 소유자 연결로 지운다 |
| 대기자 승격 시 규칙 재검증 | 충족 | `tests/registration/test_enrollment.py`: 대기 중 다른 과목을 신청해 시간이 겹치게 된 학생은 자리가 나도 승격되지 않고 사유와 함께 제외, 다음 순번 학생이 승격, 두 학생 모두 메일 수신. 승격은 `EnrollStudent`를 시스템으로 다시 호출하므로 모든 규칙을 그대로 검사. 유보석만 부족한 학생은 대기 유지, 기간이 닫힌 강좌의 대기는 만료(`test_registration_support.py`) |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `registration_preflight`, `registration_simulate`, `waitlist_promote`, `registration_release_reserved_seats`, `reference_import registration_holds` + `test_registration_commands.py`, `test_registration_support.py` |
| 2. 매뉴얼 | 관리자 매뉴얼 20장 4개 언어(원본 장 + Django 화면 차이), 9장에 수강신청 제한 CSV 절 4개 언어, 운영 명령 레퍼런스 4개 언어(명령 4개, `reference_import` 유형) |
| 3. 시더, 팩토리, 데모 | 필수 시더 `RegistrationRuleCatalogSeeder`(멱등·관리자 수정 보존 테스트), 프로파일 `yust-legacy`의 Phase 5 단계(학점 상한, 학점은행 과목), 팩토리 `tests/factories/registration.py`(수강·완료 성적, 대기, 제한, 학점 상한), 데모 `DemoRegistrationSeeder`(일괄 삽입) |
| 4. `setup_install`, `setup_demo --size=small` | 빈 DB에서 성공 |
| 5. 번역 | 앱 카탈로그 `ninefruits/registration/locale/` 신설, `convert_translations.py --fill`로 원본 값 채움(224개). 원본에 없는 문구 2개(`No`, `Edit`)는 전역 카탈로그와 같은 번역 |
| 6. 스키마 동등성 | 통과(상태 전용 마이그레이션 `registration/0001_initial`, 스키마 변경 없음) |
| 7. 테스트 대응표 | `EnrollmentTest`, `LegacyRulesTest`, `PortalRegistrationTest`, `RegistrationCommandsTest`, `ConcurrentRegistrationTest`, `RegistrationAdminTest` 완료, `AdminPagesTest` 행에 이 Phase 화면 추가 |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 모델 | `Enrollment`(과목·버전·학점·교과 구분·상한 포함 여부 스냅샷, 재수강, 성적 칸은 Phase 6), `WaitlistEntry`, `CartItem`, `RegistrationAttempt`(추가만), `RegistrationHold`, `RegistrationOverride`, `RegistrationRuleSet`, `RegistrationRule`(빈 매개변수는 NULL), `CreditLimitPolicy`(`applicable_to`). 부분 unique 인덱스 3개는 같은 이름으로 `Meta`에 문서로 선언 | `ninefruits/registration/models/` |
| 범위 조회 | `visible_to`: 수강(볼 수 있는 학적, `enrollments.view`·`registration.manage`·`grades.view` 개설 조직 범위, 담당 강좌), 대기(학적 또는 `registration.manage` 범위), 장바구니·시도 기록(학적), 제한·예외(전역 권한 또는 볼 수 있는 학적). 8가지 사용자 × 6개 테이블에서 RLS 결과와 같음(테스트) | `models/enrollment.py`, `models/holds.py`, `tests/registration/test_registration_access.py` |
| 열거형 | `AttemptAction`, `AttemptOutcome`, `EnrollmentSource`, `EnrollmentStatus`, `GradeStatus`(원본 Grading 열거형, 라벨이 registration 그룹), `HoldType`, `HoldSource`, `RuleCode`(`is_core`, `overridable`, 설명), `RuleSeverity`, `WaitlistStatus` | `registration/enums.py` |
| 규칙 10종 | `WindowRule`, `SectionOpenRule`, `HoldRule`, `StudentStatusRule`, `EligibilityRule`, `DuplicateCourseRule`, `TimeConflictRule`(허용 겹침), `CreditLimitRule`, `RequisitesRule`(대체과목·최소 성적·동시수강, 같은 사람의 다른 학적 이력 인정), `RepeatCourseRule`(허용·최대 횟수·기준 성적) | `registration/rules/` |
| 엔진, 카탈로그 | `RuleCatalog`(평가 순서), `RegistrationRuleEngine`(모든 규칙 결과를 모음, 학기 규칙 세트 설정 또는 기본값, 예외·직원 면제·직원의 기간 면제), `RegistrationContext`, `RuleCheck`/`RuleResult`/`RuleEvaluation`/`RegistrationOutcome` | `registration/services/`, `registration/data.py` |
| 좌석 | `SeatAllocator`: 트랜잭션 안 강좌 행 `select_for_update`, 유보석(대상 학생 우선, 전환 시각 전까지 남는 유보석 제외), 카운터만 갱신(`updated_at` 없음, 감사 트리거가 무시), 표시용 잔여석 | `services/seat_allocator.py` |
| Action | `EnrollStudent`(규칙은 잠금 밖, 좌석은 잠금 안, 부분 unique 위반 `IntegrityError` → "이미 신청", 대기 등록, 직원 사유·감사 `enrollment.staff_enrolled`), `DropEnrollment`(취소·철회, 감사 `enrollment.staff_dropped|withdrawn`, `EnrollmentDropped`), `LeaveWaitlist`, `ManageCart`, `ManageHolds`(제한 설정·해제, 예외 허용·취소, 감사 4종), `PrepareRuleSet`(복사 또는 기본값, 감사), `PromoteWaitlist`(시스템 컨텍스트, 재검증, 만료, 메일), `ReleaseReservedSeats` | `registration/actions/` |
| 이벤트, 작업 | `EnrollmentConfirmed`, `EnrollmentDropped`(LMS 리스너는 Phase 12). `EnrollmentDropped` → 커밋 뒤 `registration.promote_waitlist`(강좌별 Redis 잠금 60초). beat `registration.release_reserved_seats`(5분), `registration.promote_waitlists`(매시) | `events.py`, `listeners.py`, `tasks.py`, `config/celery.py`(Phase 0에 선언됨) |
| 알림 | 대기 결과 메일 3종(승격, 제외, 만료). 학생 계정 언어로 | `notifications.py` |
| 정책 | 수강, 대기, 시도 기록(읽기 전용), 제한·예외(삭제 없음), 규칙 세트·규칙·학점 상한(`ReferenceDataPolicy` + `registration_rules.manage`) | `policies.py` |
| 관리 화면 | 수강 현황(학기·상태 기본 필터, 학번·이름 검색, 학생 수강신청, 행별 취소·철회), 수강신청 제한(적용 중 기본 필터, 제한 설정, 해제, CSV 가져오기), 규칙 예외(허용, 취소), 수강신청 규칙(학기 규칙 준비, 규칙 목록 → 규칙별 편집 화면, 규칙별 매개변수), 학점 상한(대상 조건 입력), 수강신청 기록(읽기 전용, 충족하지 못한 규칙), 개설강좌 화면 수강생·대기자 탭과 학생 수강신청·지금 승격·대기 제외 | `registration/admin/`, `offering/admin/sections.py`(믹스인 연결) |
| 포털 | `/portal/registration/`: 학기 선택, 기간 상태(열림·장바구니만·시작 시각), 학점/상한, 학생 시간표(Phase 4 공용 템플릿, 휴대폰은 요일별 목록), 신청 내역과 취소·철회, 대기 순번과 대기 취소, 장바구니와 모두 신청, 강좌 검색(HTMX 부분 응답)과 신청·장바구니·대기 신청. 버튼은 폼이라 자바스크립트 없이 동작. 사용자별 분당 30회 제한(django-ratelimit). 메뉴는 학생 persona | `registration/views/portal.py`, `templates/registration/portal/` |
| CSV | `registration_holds`(원본 열과 규칙, 행마다 새 제한, 출처 `import`, `registration_holds.manage` 권한) | `registration/importers.py` |
| 명령 | `registration_preflight`(종료 코드 2), `registration_simulate`(저장·기록 없음, `--term`, `--at`), `waitlist_promote`(AuditedCommand), `registration_release_reserved_seats` | `registration/management/commands/` |
| 시더 | 필수 `RegistrationRuleCatalogSeeder`, 프로파일 단계 `yust_legacy_registration.seed_registration_rules`, 데모 `DemoRegistrationSeeder` | `setup/seeders/` |
| 매뉴얼 | 관리자 20장, 9장 수강신청 제한 절, 운영 명령 레퍼런스. 4개 언어 | `docs/manual/*/` |

### 데모 시더 속도

원본 데모 수강신청은 학생마다 `EnrollStudent`를 호출했다(원본 `setup:demo --size=large` 전체 65분). 이식본은 이번 학기 수강을 같은 규칙(수강 대상, 같은 과목, 시간 중복, 학점 상한, 선수과목, 재수강, 유보석·일반석)으로 메모리에서 판정하고 수강, 시도 기록, 좌석 카운터를 일괄 삽입·갱신한다. 대기자 강좌, 제한 2건, 규칙 세트는 원본처럼 Action을 거친다. 시도 기록의 규칙별 결과도 엔진과 같은 모양으로 남긴다.

| 크기 | 학적 | 이번 학기 수강 | 시도 기록 | `setup_demo` 전체 | 그중 수강신청 시더 |
|---|---|---|---|---|---|
| small | 104 | 272 | 523 | 5.2초 | 0.8초 |
| medium | 2,004 | 1,522 | 11,054 | 10.6초 | 3.9초 |
| large | 20,004 | 1,522 | 114,103 | 58.6초 | 34.1초 |

medium 이상에서 수강 수가 같은 것은 데모 강좌 수(학기당 52개)와 정원이 크기와 관계없이 같기 때문이다(원본과 같은 편성 규칙). 학생이 늘면 정원 마감 거절 시도가 늘어난다. 큰 크기의 시간 대부분은 시도 기록 11만 건(행마다 규칙 10개 결과 JSON)의 삽입이다.

## 4. 계획과 달라진 점

| 항목 | 계획/원본 | 실제 | 이유 |
|---|---|---|---|
| 데모 이번 학기 수강 | 원본: 학생마다 `EnrollStudent`(직원, 기간 면제) | 같은 규칙으로 메모리 판정 후 일괄 삽입. 직원 신청 업무 감사(`enrollment.staff_enrolled`)는 남기지 않음(데이터 변경 트리거 기록은 남음) | 작업 지시(일괄 삽입). 감사 행 수만큼 느려지고 데모 자료라 의미가 없다 |
| 대기 인원 세기와 순번 | 원본: 요청 사용자 컨텍스트에서 `count()` | 시스템 컨텍스트에서 센다 | RLS 아래 학생은 자기 대기 행만 보여 대기 정원과 순번이 틀어진다(원본에도 있는 문제). 대기 정원 초과 신청을 막기 위해 |
| 신청 시 장바구니 삭제, 대기 → 승격 표시 | 원본: 요청 사용자 컨텍스트 | 시스템 컨텍스트(권한 확인 뒤) | 학생의 대기 행 정책은 `waiting`, `removed`만 허용해 본인 신청 때 `promoted` 표시가 DB에서 거부된다. 직원 신청 때 학생 장바구니가 RLS로 지워지지 않던 문제도 같이 해결 |
| 즉시 승격(관리 화면) | 원본: 요청 사용자로 실행 | `PromoteWaitlist`는 항상 시스템 컨텍스트 | 시스템 승격의 시도 기록(`actor_id` NULL)은 시스템 컨텍스트에서만 RLS를 통과한다 |
| 수강생·대기자 탭 | 원본: 관계 관리자(표 + 행 작업 모달) | 개설강좌 화면의 읽기 전용 탭(표) + 행 링크(취소·철회·대기 제외는 사유 입력 화면) + 화면 위 버튼(학생 수강신청, 지금 승격) | Django 인라인은 저장 폼에 관리 폼이 필요해 기존 개설강좌 저장(테스트 포함)을 깨뜨린다. 읽기 전용 필드셋 탭은 저장 데이터가 없다 |
| 규칙 편집 | 원본: 관계 관리자 모달(규칙별 매개변수 표시) | 규칙 세트 화면의 규칙 목록 + 규칙별 편집 화면(그 규칙의 매개변수만) | 인라인 폼셋은 행마다 다른 필드를 둘 수 없다 |
| 학생·강좌 선택 | 원본: 검색 선택 상자 | 학번 입력(볼 수 있는 학적에서 찾음), 강좌는 이번 학기 공개 강좌 선택 또는 `과목코드-분반` 입력, 과목은 코드 입력 | unfold 자동 완성에는 별도 검색 뷰가 필요. 학적 수만 명에도 화면이 가볍다 |
| 대화상자 | 원본: 모달 | 사유 입력 화면(원본 모달의 항목과 같음), 확인만 필요한 동작은 확인 화면 | Phase 1~4와 같은 `render_action_form` 방식 |
| 포털 메시지 | Livewire 상태(`messageTone`) | 동작 뒤 세션에 담아 다음 화면에 표시(`data-tone`) | 버튼이 폼이라 POST 후 되돌아온다(HTMX는 블록만 교체) |
| 요청 제한 | 원본: 신청 관련 동작에 분당 30회 | 같음(신청, 대기 신청, 장바구니 담기, 모두 신청). django-ratelimit, 사용자 키 | — |
| 제한·예외 `visible_to` | 원본 관리 화면: 볼 수 있는 학적 | 전역 `registration_holds.manage`이거나 볼 수 있는 학적 | RLS 정책이 범위 권한의 학적 조회를 사용자 RLS 아래에서 하므로, 범위 권한만으로는 학적을 볼 수 없는 직원에게 더 보이지 않는다(테스트로 확인) |
| 제한 CSV의 작성자 | 원본: 가져오기 실행 사용자 | 요청(또는 작업) 컨텍스트의 사용자. 명령(`reference_import`)으로 넣으면 비어 있음 | 가져오기 리소스가 가져오기 행을 모른다(Phase 1 구조) |
| 승격 작업 고유성 | 원본: `ShouldBeUnique`(60초) | 강좌별 Redis 잠금(`cache.add`, 60초, 실행 중 유지), 매시 안전망 | 계획 13.1 |
| `registration_release_reserved_seats` | 원본: 감사 없는 명령 | 같음(`StatusCommand`). DB 시스템 컨텍스트에서 실행 | 원본과 같이 5분마다 도는 명령을 감사에 남기지 않는다 |
| 규칙 카탈로그 시더 | 원본: 없음(카탈로그는 코드, 행이 없으면 기본값) | 필수 시더가 기존 규칙 세트에 빠진 규칙 행을 기본값으로 추가 | 계획 10절 "카탈로그 동기화 시더". 새 규칙이 규칙 세트 화면에 나타난다 |
| `GradeStatus` 위치 | 원본: Grading 열거형 | `registration.enums` | 수강 테이블의 열이고 라벨이 registration 그룹. Phase 6에서 `grading.enums`로 옮겨도 된다 |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| 성적 칸 사용, 철회 W, 재수강 성적 반영 | `Enrollment`의 성적 열, `display_grade` | Phase 6 |
| 수강신청 제한의 성적 조회·증명서 효과 | `blocks_grades`, `blocks_certificates` 적용 | Phase 6, Phase 8 |
| LMS 리스너 | `EnrollmentConfirmed`, `EnrollmentDropped` → 동기화 작업 | Phase 12 |
| 직전 학기 평점에 따른 추가 학점, 대기자 수락 기한 방식 | 원본도 미구현 | 요청 시 |
| 부하 테스트, 캐시와 멱등 키 | 원본 17.7·10.7절 | Phase 13 |
| 학생·강좌 자동 완성 | 관리 화면 입력이 학번·코드 입력 | Phase 13(대량 설치 화면 점검 때) |
| 명령으로 넣은 제한 CSV의 작성자 | `created_by`가 비어 있음 | 가져오기 기반이 실행 사용자를 넘길 때 |
| 동시성 테스트 실행 | 기본 실행(`pytest`)에도 포함된다. 커밋된 픽스처를 쓰므로 `-n`으로 병렬 실행할 때는 `-m "not concurrency"`로 빼고 따로 돌린다(CI 설정과 같음) | 운영 안내 |

## 6. 실행 방법

`uv run manage.py setup_demo --size=small` 후(비밀번호 `demo-password`):

| 계정 | 볼 것 |
|---|---|
| `registrar@demo.test` | 관리 화면 **수강신청**: 수강 현황(학생 수강신청, 취소·철회), 수강신청 제한, 규칙 예외, 수강신청 규칙, 학점 상한, 수강신청 기록. 개설강좌 화면의 수강생·대기자 탭(다음 학기에 정원 2명, 대기 2명인 강좌가 하나 있다) |
| `student@demo.test` | 포털 **수강신청**: 다음 학기 장바구니(열림), 수강신청은 학년별 시차 오픈. 이번 학기로 바꾸면 신청 내역과 시간표 |
| `academic-affairs@demo.test` | 수강신청 규칙, 학점 상한 |

명령 예: `uv run manage.py registration_preflight {다음 학기 코드}`, `uv run manage.py registration_simulate {학번} {과목코드-분반}`.

## 7. 검증 결과

| 항목 | 결과 |
|---|---|
| 전체 테스트(`pytest -n 4 -m "not concurrency"`) | 732개 통과(65초). 다른 작업자(p3 입학)의 테스트 포함 |
| 동시성 테스트(`pytest -m concurrency`) | 1개 통과(12초) |
| 이 Phase 테스트(`tests/registration/`) | 61개 통과 |
| 정적 검사 | ruff format/check, `tools/checks/raw_sql.py`, `manage.py check`, `makemigrations --check --dry-run`, `naming_check`, `i18n_missing --strict` 통과 |
| 데모 시간 | 3절 표(같은 기계, 빈 DB에서 `setup_install` 뒤 `setup_demo --seed=42`. 수강신청 시더 시간은 같은 DB에서 시더만 다시 실행해 잰 값) |
