# Phase 2 인물과 학적 결과 보고

- 작성일: 2026-10-24
- 대상: 개발팀, 프로젝트 관리자
- 관련: [이식 계획 14절 Phase 2](porting-plan.md#phase-2-인물과-학적-l), 원본 [Phase 2 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-2-report.md), 원본 [ADR 0007](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0007-people-accounts-and-sign-in.md), [ADR 0003-django](decisions/0003-django-sso-oidc-client.md)

## 1. 요약

Phase 2 작업 항목을 모두 구현했다. 원래 Phase 4 몫이던 복수전공·부전공 신청(`additional_program_requests`)도 학적에 속하므로 이 Phase에서 함께 옮겼다. 전체 테스트 622개 통과(`-n 4` 30초). 이 Phase에서 추가한 테스트는 74개(`tests/person/` 67개, `tests/security/test_sign_in_methods.py`의 SSO 사례 7개) + 모델·테이블 일치 검사 11개 모델. ruff format/check, raw SQL 검사, `manage.py check`, `makemigrations --check`, `naming_check`, `i18n_missing --strict`(ko, zh_Hans, lo), 스키마 동등성 검사 모두 통과.

빈 DB에서 `setup_install --force --profile=korean-university`(2.4초)와 `setup_demo --size=small`(5.5초) 성공을 확인했다. `--size=large`(학적 20,004건, 교원 포함, Phase 4 데모 포함)는 21초다. 원본은 large에 65분이 걸렸다. 데모 인물·학적은 `bulk_create`로 넣고 학번은 연도별로 한 번에 예약한다.

## 2. 완료 기준

| 완료 기준 | 결과 | 근거 |
|---|---|---|
| 역할별 조회 범위 테스트 | 충족 | `tests/person/test_student_record_access.py`: 학적 담당(전체), 학과 조교(학과), 단과대학 조교(하위 학과 포함), 프로그램 담당, 지도교수, 학생 본인, 권한 없음 7가지 사용자에 대해 애플리케이션 범위(`visible_to`)와 DB(RLS) 결과가 같음. 범위 밖 수정은 DB에서도 0건. `test_people_admin.py`: 학과 조교가 다른 학과 학적을 열면 열리지 않음(404 → 목록으로 이동) |
| 한 사람이 여러 학적을 가질 때 학적 선택과 권한 | 충족 | `test_student_record_actions.py`: 재입학 졸업생에게 새 학적·새 학번, 기존 학적 유지. `test_portal.py`: 재입학자가 학적을 바꿔 보고 현재 학적에서만 변동 신청, 졸업 학적은 읽기 전용, RLS 아래에서 학생은 자기 학적만 봄 |
| 학적 변경 감사 기록 | 충족 | 학적 등록, 변동 신청/승인/반려/취소/직접 처리, 지도교수 배정, 병합, 초대, 복수전공 신청·결정·종료가 업무 감사에 남고, 학적 상태 변경은 트리거 데이터 변경 기록에도 남음. 인물·학적 상세 아래쪽 **변경 이력**에 표시 |
| 학번 로그인 설정 3가지 값별 동작 | 충족 | `tests/security/test_sign_in_methods.py`(학적 팩토리로 바꿈) |
| SSO 연결 사용자가 졸업 후 개인 이메일로 로그인 | 충족 | 같은 파일. SSO 흐름(가짜 OIDC 제공자) 사례 추가 |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 1. 명령과 테스트 | `people_find_duplicates` 추가(`security_reset_mfa`, `security_unlock_user`는 Phase 0에 있음), `reference_import students`/`instructors` + 테스트 |
| 2. 매뉴얼 | 관리자 매뉴얼 12~15장 4개 언어, 9장에 학생과 교원 CSV 절, 운영 명령 레퍼런스(`people_find_duplicates`, `reference_import` 유형) 4개 언어 |
| 3. 시더, 팩토리, 데모 | 필수 시더 `StatusChangeTypeSeeder`(6종, 멱등·관리자 수정 보존 테스트), 팩토리 8개(`tests/factories/person.py`), 데모 `DemoPeopleSeeder`(포털 데모 계정 4개), `--student-accounts` 재학생 계정 |
| 4. `setup_install`, `setup_demo --size=small` | 빈 DB에서 성공 |
| 5. 번역 | `i18n_missing --strict` 통과. 앱 카탈로그 `ninefruits/person/locale/` 신설, 원본 값으로 채움. 원본에 없는 새 문구 14개(변경 이력, 사진 크기 안내 등)는 직접 번역 |
| 6. 스키마 동등성 | 통과(도메인 마이그레이션은 상태 전용, `users.person_id`는 `OneToOneField`로 상태만 바뀜) |
| 7. 테스트 대응표 | 원본 10개 파일 완료로 갱신(`HardeningTest`는 CSV 수식 사례만 Phase 11) |
| 8. 결과 보고 | 이 문서 |

## 3. 작업 항목별 결과

| 계획 항목 | 결과 | 주요 위치 |
|---|---|---|
| 모델 | `Person`(PII 필드 2개 + HMAC, 사진 Media 컬렉션, `created_by` DB 기본값 `util.current_user_id()`), `Guardian`, `Instructor`, `StudentRecord`(`TargetSubject` 구현), `StudentRecordProgram`, `StudentStatusChangeType`, `StudentStatusChange`, `AdvisorAssignment`, `AccountInvitation`, `AdditionalProgramRequest`, `StudentNumberSequence`. `User.person`을 `OneToOneField`로 | `ninefruits/person/models/`, `security/models/user.py` |
| 범위 조회 | `visible_to`: 인물(전체 조회 권한, 본인, 작성자, 볼 수 있는 학적의 인물, 교원), 학적(조직·프로그램 범위, 복수전공·부전공 범위, 결정할 신청, 본인, 지도 학생, 담당 강좌 학생), 학적 변동, 복수전공 신청(`decidable_by`). RLS와 같은 결과(테스트) | `person/models/` |
| 업무 Action | 원본 14개: `RegisterStudent`, `RequestStatusChange`, `DecideStatusChange`, `RecordStatusChange`, `CancelStatusChange`, `AssignAdvisor`, `InvitePerson`, `AcceptInvitation`, `MergePeople`, `UpdateOwnContactDetails`, `RequestAdditionalProgram`, `DecideAdditionalProgramRequest`, `CancelAdditionalProgramRequest`, `EndAdditionalProgram`. 직무 분리(자기 신청 결정 금지), 신청 후 상태 변경 감지, 처리 중 신청 하나(세이브포인트 + unique 위반 변환) | `person/actions/` |
| 학번 생성기 | 원본과 같은 단일 upsert(`ON CONFLICT DO UPDATE ... RETURNING`), 이미 쓰인 번호 건너뛰기(`util.student_number_exists`). 대량용 `next_many`(블록 예약) | `person/services/student_numbers.py` |
| 현재 학적 | 세션에 고른 학적(`CurrentStudentRecord`) | `person/services/current_record.py` |
| 정책, persona | 정책 6종 + 학적 변동 유형(기준정보 정책), persona 판정 4종(학생, 졸업생, 교원, 지도교수). 지원자 판정은 Phase 3이 같은 `register_detector`로 추가 | `person/policies.py`, `person/personas.py` |
| 설정 | `student_records` 그룹(학번 형식, 초대 유효 일수, 동시 복수전공·부전공 수), 데이터 마이그레이션 `0008_p2_additional_program_limits`, 관리 화면 **설정 > 학적** | `person/settings.py`, `person/settings_pages.py` |
| 관리 화면 | 인물(목록·검색: 이름 변형·신분번호 정확 일치, 병합됨 필터, 상세 탭: 학적·보호자, 사진 업로드, 변경 이력, **주민등록번호/여권번호 보기**(사유 → 별도 화면에 한 번 표시, 보안 로그), 계정 초대, 중복 병합), 학적(목록·필터, **학적 등록**(기존/새 인물), 상세 탭: 학적 변동·지도교수·복수전공, **학적 변동 처리**, **지도교수 배정**, 복수전공 종료, 변경 이력, CSV 가져오기), 학적 변동(처리 대기 기본 필터, 행별 승인/반려), 학적 변동 유형(시스템 유형의 전이 고정), 교원(재직 필터, 등록 시 기존/새 인물, CSV 가져오기), 복수전공·부전공 신청(행별 승인/반려) | `person/admin/` |
| CSV 가져오기 | `students`, `instructors` 등록(`importing.registry`), 인물 열 공통, 신분번호로 기존 인물 연결(재입학), 행 세이브포인트 안에서 인물 저장(거부된 행은 인물도 남지 않음) | `person/importers.py` |
| 초대, 사진 | 초대 링크 `/invitations/<token>/`(SHA-256만 저장, 6회/분 제한, 수락 시 이메일 인증 처리·로그인), 사진 `/people/<id>/photo/`(권한 확인 뒤 비공개 저장소에서 내려 줌) | `person/views/`, `person/urls.py` |
| 포털 | **내 학적**(학적 선택, 변동 신청·취소, 복수전공·부전공 신청·취소, 변동 이력), **내 정보**(연락처, 보호자), **지도 학생**. 메뉴는 persona별. 첫 화면 환영 문구는 인물 이름 | `person/views/portal.py`, `templates/person/portal/` |
| SSO, 학번 로그인 | 자체 OIDC 클라이언트(PKCE, state, nonce, JWKS 서명 검증), `/auth/sso/<key>/redirect|callback/`, 연결 방식(직접 연결: 비밀번호 재확인 / 학교 이메일 자동 연결), `trusts_mfa`가 아니면 allauth 로그인 단계의 2단계 인증, 로그인 화면 버튼, 설정 화면의 리디렉션 URI 수정. 학번 로그인·잠금은 Phase 0 구현을 학적 모델로 확인 | `security/services/oidc.py`, `security/views_sso.py`, `security/stages.py` |
| 명령 | `people_find_duplicates`(같은 신분번호 해시 또는 같은 로마자 성명+생년월일, 종료 코드 2, 감사 안 함) | `person/management/commands/` |
| 시더 | 필수 `StatusChangeTypeSeeder`, 데모 `DemoPeopleSeeder`(bulk, `--seed` 재현), `enrolled_student_accounts`(`--student-accounts`) | `setup/seeders/essential/status_change_type.py`, `setup/seeders/demo/people.py` |
| 매뉴얼 | 관리자 12~15장(원본 장을 Django 화면·명령으로: 추가 버튼, 표시 해제 화면, 변경 이력, 병합 대상 선택 목록, SSO 리디렉션 URI, `uv run manage.py`), 9장 학생과 교원 절, 명령 레퍼런스. 4개 언어 | `docs/manual/*/` |

## 4. 계획과 달라진 점

| 항목 | 계획 | 실제 | 이유 |
|---|---|---|---|
| SSO 구현 | allauth `socialaccount` `openid_connect` 제공자 | 자체 OIDC 클라이언트 + allauth 로그인 단계 | allauth 제공자는 nonce를 쓰지 않고 토큰 엔드포인트에서 받은 ID 토큰의 서명 검증을 건너뛴다. 원본(ADR 0007)과 원본 테스트가 요구하는 검증 수준을 지키기 위해. [ADR 0003-django](decisions/0003-django-sso-oidc-client.md) |
| SSO 리디렉션 URI | (Phase 0 설정 화면) `/accounts/oidc/<key>/login/callback/` | `/auth/sso/<key>/callback/` | 위 결정에 따름. 설정 화면 표시를 고침 |
| 복수전공·부전공 신청 | Phase 4 | Phase 2 | 학적에 속하는 기능이라 이번 Phase로 옮김(작업 지시) |
| 학적 변동 메뉴 숫자 | 원본: 메뉴 옆에 처리 대기 건수 | 없음 | 관리 메뉴(`adminpanel.navigation`)에 배지 기반이 없다. 목록 기본 필터가 처리 대기 |
| 병합 대상 선택 | 원본: 검색해 고르는 선택 상자 | 볼 수 있는 미병합 인물 선택 목록 | unfold 자동 완성은 별도 검색 뷰가 필요. 대량 설치에서는 Phase 13에 자동 완성으로 바꿀 것 |
| 표시 해제 | 원본: 알림(notification)으로 값 표시 | 사유 입력 → 별도 화면에 한 번 표시, `Cache-Control: no-store` | Django 메시지는 세션에 저장되므로 값이 세션에 남는다 |
| 변경 이력 탭 | 이식 계획: 학생 상세 변경 이력 탭 | 인물·학적 상세 아래쪽 **변경 이력**(최근 50건, 감사 권한이 있으면 상세 링크) | 원본 Filament 화면에는 없음. 계획 문구를 따름 |
| 인물 가시성 확장 | 원본: 지원서를 볼 수 있는 인물 포함 | `PERSON_VISIBILITY` 확장점, 병합 시 지원서는 SQL로 옮김 | 지원서 모델은 Phase 3 |
| 담당 강좌 학생 범위 | 원본: `Enrollment`·`Section` 모델 질의 | 상수 SQL 하위 질의(`enrollments`, `section_instructors`) | 모델이 Phase 4·5. RLS 함수 `util.taught_student_record_ids()`와 같은 조건 |
| 초대 메일 | 원본: 큐 알림 | 트랜잭션 커밋 뒤 바로 발송(평문) | Phase 0 보안 메일과 같은 방식. 알림 테이블 기반은 이후 |
| 계정 표시 이름 | `str(user)` = 이름 또는 이메일 | 인물이 연결된 계정은 인물 이름 | 원본 Phase 2 수정 사항(포털 환영 문구) |

## 5. 남은 일과 위험

| 항목 | 내용 | 시점 |
|---|---|---|
| 지원자 persona, 지원자 → 학생 전환 | `register_detector`, `PERSON_VISIBILITY`, `RegisterStudent` 사용 | Phase 3 |
| 담당 강좌 학생 범위 | 강좌·수강 모델이 생기면 ORM 질의로 바꿀 수 있음(결과는 같음) | Phase 4·5 |
| 병합 대상 자동 완성 | 인물이 많은 설치에서 선택 목록이 길다 | Phase 13 |
| 학적 변동 처리 대기 배지 | 관리 메뉴 배지 기반 | 필요 시 |
| JWKS 캐시 | 제공자가 서명 키를 바꾸면 최대 1시간 동안 로그인이 실패할 수 있다(원본과 같음) | 운영 안내 |
| 병합과 RLS | 병합은 인물 관리 권한으로 실행하지만 학적 행 이동은 `student_records.manage` RLS를 거친다. 학적 관리 권한이 없는 담당자의 병합은 DB에서 일부 행이 옮겨지지 않을 수 있다(원본과 같은 구조) | 역할 설계 시 확인 |
| 관리 화면 캡처 | 매뉴얼 화면 캡처 | Phase 13 |

## 6. 실행 방법

`uv run manage.py setup_demo --size=small`. 포털 데모 계정(비밀번호 `demo-password`):

| 계정 | 내용 |
|---|---|
| `student@demo.test` | 재학생. 지도교수 있음 |
| `alumni@demo.test` | 졸업생 |
| `readmitted@demo.test` | 졸업 후 재입학. 학적 2개 |
| `instructor@demo.test` | 교원, 위 재학생의 지도교수 |
