# Phase 1 기준정보 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 1](porting-plan.md#phase-1-기준정보-m), 원본 [Phase 1 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-1-report.md), 원본 [ADR 0006](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0006-reference-data-model.md)

## 1. 요약

Phase 1 작업 항목을 모두 구현했다. 테스트 488개 통과(직렬 34초, `-n 4` 13초). 이 Phase에서 추가한 테스트는 98개(+ 모델·테이블 일치 검사 21개 모델). ruff format/check, raw SQL 검사, `manage.py check`, `makemigrations --check`, `naming_check`, `i18n_missing --strict`(ko, zh_Hans, lo), 스키마 동등성 검사 모두 통과.

빈 DB에서 `setup_install --force --profile=korean-university`(5초)와 `setup_demo --size=small`(2.4초), `--size=large`(3.7초) 성공을 확인했다. 기준정보 테이블의 데모 행 수는 원본 small 데모(`/home/user/reference/demo-small-counts.txt`)와 같다(조직 10, 프로그램 5, 건물 3, 강의실 24, 학년도 2, 학기 3, 교시 10, 교과 구분 8, 성적 척도 1/등급 11, 국가 249, 언어 184, 코드 목록 4).

## 2. 완료 기준

| 완료 기준 | 결과 | 근거 |
|---|---|---|
| 신규 대학이 화면과 CSV만으로 기준정보 초기 세팅 가능 | 충족 | 관리 화면 14개 + CSV 가져오기 기록 화면, CSV 가져오기 5종(조직 단위, 프로그램, 건물, 강의실, 코드 값). `tests/admin/test_reference_admin.py`, `tests/importing/`. 관리자 매뉴얼 5장에 입력 순서 |
| 여러 학기가 서로 다른 업무 기간에 동시에 존재해도 `TermResolver`가 업무별로 올바른 학기를 반환 | 충족 | `tests/term/test_term_resolver.py`: 지난 학기 성적 이의, 현재 학기 성적 입력, 다음 학기 수강신청이 같은 시각에 각각 반환. 학년별 시차 오픈, 기관 시간대 날짜 판단, `term_inspect` |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `setup_install`, `setup_demo`, `reference_import`, `term_inspect` + 테스트 |
| 2. 매뉴얼 | 운영 명령 레퍼런스 4개 언어, 관리자 매뉴얼 5~11장 4개 언어 |
| 3. 시더, 팩토리, 데모 | 필수 시더 5종(역할 템플릿, 국가, 언어, 코드 목록 유형, 조직 단위 유형) 멱등성 테스트, 프로파일 2종, 데모 기준정보, 팩토리 6개 모듈(19개 모델) |
| 4. `setup_install`, `setup_demo --size=small` | 빈 DB에서 성공 |
| 5. 번역 | `i18n_missing --strict` 통과. 원본 `lang/`에 없는 새 문구 25개(CSV 가져오기 기록 화면 등)는 직접 번역 |
| 6. 스키마 동등성 | 통과(도메인 마이그레이션은 상태 전용) |
| 7. 테스트 대응표 | 원본 13개 파일 완료로 갱신(`porting/test-mapping.md`) |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 코드 데이터, 국가, 언어 | `Country`, `Language`, `LookupType`, `LookupValue`(`of_type`). 시스템 목록은 코드 변경·삭제 불가 | `ninefruits/institution/models/` |
| 조직 단위, 승계, 프로그램 | `OrgUnitType`, `OrgUnit`(유효기간, `effective_on`, `descendant_ids_of`, `ancestor_ids`), `OrgUnitSuccession`, `Program`. 순환 방지·생성 열은 DB 그대로 | `ninefruits/organization/` |
| 조직 개편 | `ReorganizeOrgUnit`(전날 종료, 승계 연결, 감사 `org_unit.reorganized`) | `organization/actions/` |
| 건물, 강의실 | `Building`, `Room`(용도는 코드 목록 `room_type`) | `ninefruits/facility/` |
| 학년도, 학기, 세션, 업무 기간, 교시 | `AcademicYear`, `TermType`, `Term`(생성 시 전체 학기 세션 자동 생성, 날짜 변경 시 따라감, 밖으로 나가는 세션이 있으면 거부: 원본 모델 이벤트를 `save()`로), `TermSession`, `TermWindow`(과목 업무만 세션, 비면 전체 학기 세션), `TimeSlot` | `ninefruits/term/models/` |
| 학기 상태, 세션 업무 기간 복사 | `ChangeTermStatus`(전이 규칙, 감사), `CopySessionWindows`(시작·종료 기준 이동) | `term/actions/` |
| `TermResolver` | `in_session`, `open_windows`, `terms_open_for`, `is_open_in_session`, `next_window`, 기관 시간대 날짜 | `term/services/term_resolver.py` |
| `TargetCriteria`, `TargetSubject` | 불변 dataclass + Protocol, jsonb 필드 `TargetCriteriaField`(비면 `{}` 저장), 관리 화면 입력 필드와 요약 | `ninefruits/core/targeting.py`, `institution/target_criteria_fields.py` |
| 교과 구분, 성적 척도 | `CourseCategory`, `GradeScale`, `GradeScaleItem`, `SaveGradeScale`(기본 척도는 설치 때 고정), 등급 열거형 `GradeAppliesTo`, `AcademicStanding` | `ninefruits/curriculum/`, `ninefruits/grading/` |
| 권한 | 원본 정책 10종을 `ReferenceDataPolicy`(조회는 `reference_data.view`, 변경은 자원별 관리 권한)로 등록 | `institution/policies.py` |
| CSV 가져오기 기반 | django-import-export `ModelResource` 기반 `ReferenceResource`(원본 Laravel 검증 규칙과 메시지, 코드로 찾아 갱신, 언어별 열, 행마다 세이브포인트), `imports`/`failed_import_rows` 모델, Celery 청크 작업, 작은 파일은 요청 안에서 처리(`IMPORT_SYNC_MAX_ROWS`, 기본 500), 실패 행 CSV 내려받기, 가져오기 기록 화면 | `ninefruits/importing/` |
| Importer | 5종: 조직 단위, 프로그램, 건물, 강의실, 코드 값. 등록기(`registry.register`)로 이후 Phase가 학생·교원·교과목·수강 제한 추가 | `importing/importers.py`, `registry.py` |
| 관리 화면 | 국가, 언어, 코드 목록(+값 인라인), 조직 단위 유형, 조직 단위(현재 유효 필터 기본, 승계 인라인, 조직 개편 대화상자), 프로그램, 건물, 강의실, 학기 종류, 학년도, 학기(세션 탭, 업무 기간 탭과 대상 조건, 상태 변경 대화상자, 세션 업무 기간 복사), 교시(벽시계 시각), 교과 구분, 성적 척도(+등급 인라인), CSV 가져오기 기록. 이름 다국어 검색, 사용 중인 행 삭제 시 안내, 일괄 삭제 없음, 목록마다 **CSV 가져오기** 버튼 | `*/admin.py`, `institution/admin_support.py` |
| 관리 화면 시간대 | 관리 화면 요청은 기관 시간대로 표시·입력(`AdminTimezoneMiddleware`), 저장은 UTC | `ninefruits/adminpanel/middleware.py` |
| 범위 할당의 조직·프로그램 선택 | 역할 할당 화면의 숫자 ID 입력을 조직 단위·프로그램 선택 목록으로 교체, `describe_scope`를 모델 조회로 | `security/admin.py`, `security/models/role_assignment.py` |
| 시더 구조 | `Seeder`(`run()`, `call()`), `seed_row`/`seed_rows`(빠진 행·빠진 언어만 추가, 관리자 수정 보존), `essential/`, `profiles/`(`SetupProfile`, `ninefruits/setup/conf.py`), `demo/`(`DemoOptions`: 크기 tiny/small/medium/large, 시드, 운영 거부) | `ninefruits/setup/seeders/` |
| 필수 시더 | 역할 템플릿(`sync_role_templates`), 국가 249(pycountry + Babel CLDR 이름), 언어 184, 시스템 코드 목록 4, 조직 단위 유형 5 | `setup/seeders/essential/` |
| 프로파일 시더 | `korean-university`(학기 종류, 교과 구분, 4.5 척도, 교시, 강의실 용도, 입학 구분, 지원 서류), `yust-legacy`(4.3 척도 + 한국 대학) | `setup/seeders/profiles/` |
| 데모 시더 | 데모 계정 6개(`.test`), 데모 기준정보(조직, 프로그램, 건물·강의실 일괄 삽입, 오늘 기준 지난·현재·다음 학기와 업무 기간) | `setup/seeders/demo/` |
| 명령 | `setup_install`, `setup_demo`(`--student-accounts`는 비공개 저장소 `load-accounts.csv`), `reference_import`, `term_inspect` | `*/management/commands/` |
| 매뉴얼 | 관리자 5~11장(원본 장을 Django 화면·명령으로), 운영 명령 레퍼런스, 4개 언어 | `docs/manual/*/` |
| 번역 | 앱별 카탈로그 7개 신설(`institution`, `organization`, `facility`, `term`, `curriculum`, `grading`, `importing`), `convert_translations.py --fill`로 원본 값 채움 | `ninefruits/*/locale/` |

## 4. 계획과 달라진 점

| 항목 | 계획 | 실제 | 이유 |
|---|---|---|---|
| Importer 수 | 6개 | 5개 | 원본 Phase 1 보고와 `ReferenceImporters` 기준 기준정보 가져오기는 5종(조직 단위, 프로그램, 건물, 강의실, 코드 값). 학생·교원·교과목·수강 제한은 해당 Phase |
| 전체 학기 세션 | 원본 v1.0.0 기준 | 포함 | 원본 Phase 1 보고는 "만들지 않음"이었으나 v1.0.0에는 `term_sessions`가 있다. 원본 최종 코드를 따랐다(모델 이벤트 → `Term.save()`) |
| CSV 가져오기 화면 | django-import-export 관리 화면 연동 | 리소스는 django-import-export, 화면은 자체 업로드 화면 + 가져오기 기록 화면 | 원본은 부분 성공(실패 행만 기록)이고 django-import-export 관리 화면은 오류가 있으면 전체를 되돌린다. 원본처럼 행마다 세이브포인트로 처리하고 결과·실패 행을 기록 화면에 보인다 |
| 가져오기 완료 알림 | 원본: 관리 화면 알림(DB 알림) | 가져오기 기록 화면과 메시지 | DB 알림(`notifications` 테이블) 기반이 아직 없다. 작은 파일은 바로 결과를 보이고, 큐로 간 것은 기록 화면에서 확인 |
| 열 이름 짝짓기 | 원본: 가져오기 창에서 열 수동 매핑 | 열 이름이 맞아야 하고 모르는 열은 무시 | 명령과 같은 규칙. 원본의 `name_zh_CN`은 `name_zh-hans`로 받아들인다 |
| 언어별 열 이름 | `name_zh_CN` | `name_zh-hans`(Django 언어 코드) | 언어 코드 체계(ADR 없이 CLAUDE.md 규칙). 원본 이름도 허용 |
| 국가·언어 데이터 | symfony/intl | pycountry(코드) + Babel(CLDR 이름) | Python에 같은 CLDR 데이터. `pycountry` 의존성 추가 |
| `term_inspect --at` | 원본: Carbon 파싱 | ISO 형식 + 선택적 IANA 시간대 이름, 시간대 없으면 UTC | 원본과 같은 해석(서버 시간대) |
| 필수 시더의 학적 변동 종류 | 원본 `StatusChangeTypeSeeder` | Phase 2 | 학적 모델이 Phase 2. `EssentialSeeder.SEEDERS`에 추가하면 된다 |
| 프로파일의 후속 단계 | 원본 `korean-university`는 강의평가 양식·증명서 종류·시험 종류, `yust-legacy`는 학점 상한·성적 정책도 만든다 | Phase 1 부분만 | 테이블이 해당 Phase에서 생긴다. 각 Phase가 `LATER_PHASE_STEPS`에 단계를 추가한다 |
| `setup_demo --student-accounts` | 재학생 계정 생성 | 파일만 만들고 계정 0개 | 학적이 Phase 2. `DemoSeeder.STUDENT_ACCOUNT_PROVIDERS`로 연결 |
| 명명 검사 | msgctxt는 snake_case 그룹 이름만 | 점으로 이은 그룹 경로(`reference.fields`)도 허용 | `convert_translations.py`가 원본 그룹 안에서도 번역이 갈리는 문구에 이 형식을 만든다(도구 문서와 검사가 어긋나 있었음) |
| 데모 기준정보 언어 | 원본 en, ko, zh_CN | en, ko, zh-hans | 원본과 같은 범위 |
| 교시 입력 오류 안내 | 원본 10장의 "Phase 4 이전 교시 시각 오류" 문단 | 삭제 | Django 구현에는 그 오류가 없다(`time` 열은 변환하지 않음, 테스트로 고정) |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| 학생 기준 대상 조건 판단 | `TargetSubject` 구현(학적), 학생·교원 CSV | Phase 2 |
| 학적 변동 종류 필수 시더, 화면 | `StatusChangeTypeSeeder`, 기준정보 메뉴의 학적 변동 종류 | Phase 2 |
| 교과목 CSV, 교과목 버전 | `importing.registry.register` | Phase 4 |
| 프로파일 후속 단계 | 강의평가 양식(7), 증명서(8), 시험(9), 학점 상한(5), 성적 정책(6) | 각 Phase |
| DB 알림 | 가져오기 완료 알림을 관리 화면 알림으로 | 알림 기반이 생길 때 |
| 큰 파일 동시 처리 | 큐 작업이 병렬로 돌면 같은 파일의 상위 조직이 다른 청크에 있을 때 하위 행이 실패할 수 있다(원본도 같음). 실패 행을 다시 가져오면 된다 | 운영 안내(매뉴얼 9장의 정렬 규칙) |
| 다른 앱 카탈로그 서식 | `i18n_makemessages` 재실행으로 security, portal, 전역 카탈로그의 줄바꿈·위치 주석이 바뀌었다(번역 내용 변화 없음, 확인함) | — |
| 관리 화면 캡처 | 매뉴얼 화면 캡처 | Phase 13 (데모 데이터로) |
