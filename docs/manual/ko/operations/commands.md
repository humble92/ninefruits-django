# 관리 명령 레퍼런스

- 대상: IT 운영자
- 기준: 이 저장소의 Ninefruits 앱(`ninefruits/*/management/commands/`)에 등록된 명령 전체와 운영에 쓰는 Django 내장 명령. 명령을 추가하면 이 문서(4개 언어)에도 `### \`명령\`` 항목을 추가해야 CI가 통과한다(`tests/tooling/test_command_documentation.py`).

## 공통 사항

모든 명령은 `uv run manage.py {명령}`으로 실행한다. Docker 개발 환경에서는 `docker compose exec app uv run manage.py {명령}`.

| 항목 | 규칙 |
|---|---|
| 이름 | 원본 `{context}:{action}`을 `{context}_{action}`으로 바꾼 이름이다(Django 명령 이름에 `:`를 쓸 수 없다). 예: `term:close` → `term_close` |
| 감사 기록 | 데이터를 바꾸는 명령(아래 "감사: 기록")은 실행할 때마다 업무 감사(로그 `command`)에 명령, 인수, 옵션, OS 사용자, 종료 코드, 결과를 남긴다. 관리 화면 **감사 > 업무 감사 기록**에서 확인한다 |
| 실행 ID | 실행마다 `cmd-`로 시작하는 ID가 요청 ID 자리에 붙는다. 업무 감사, 그 실행이 바꾼 데이터 변경 기록, 실행이 넣은 Celery 작업이 같은 ID를 가지므로 "이 변경이 어느 명령에서 왔는가"를 ID로 찾는다. `--actor`는 실행자가 적는 값이라 데이터 변경 기록의 사용자 칸에는 넣지 않는다(실제 실행자는 OS 사용자) |
| `--actor=<이메일>` | 감사 기록 명령에 공통으로 있다. 책임자 관리자 계정을 기록한다. 없는 이메일이면 실행하지 않는다 |
| `--dry-run` | 변경 없이 결과만 출력한다. 되돌리기 어려운 작업에 있다 |
| `--force` | 확인 질문 없이 실행한다(스케줄, 배포 스크립트용) |
| `--reason=` | 사유가 필요한 명령에 있다 |
| 종료 코드 | 0 성공, 1 실패 또는 취소, 2 점검 명령이 문제를 발견함 |
| DB 컨텍스트 | 실행 중에는 DB 세션의 수행자가 `system:command:{명령}`으로 설정되어 데이터 변경 기록(트리거)에 남는다 |

## Django 내장 명령

### `migrate`

- 용도: DB 마이그레이션을 적용한다. Django 기본 명령을 감싼 Ninefruits 명령으로, `--database`를 주지 않으면 스키마 소유자 연결(`migrator`, 역할 `app_migrator`)을 쓴다. 애플리케이션 연결(`app_runtime`)은 DDL 권한이 없다. `showmigrations`, `sqlmigrate`도 같은 방식으로 `migrator` 연결을 기본값으로 쓴다.
- 실행 시점: 최초 설치, 그리고 배포할 때마다(이후 Phase에서는 `setup_install`이 함께 실행한다).
- 옵션: Django `migrate`와 같다(`app_label`, `migration_name`, `--plan`, `--check`, `--database`).
- 감사: 기록 안 함(스키마 변경은 마이그레이션 이력 `django_migrations`에 남는다)
- 예시

  ```bash
  uv run manage.py migrate
  uv run manage.py migrate --plan
  ```

- 실패 시: 권한 오류면 [설치 매뉴얼](installation.md)의 DB 역할 준비(`db/sql/roles/`)를 확인한다.

### `collectstatic`

- 용도: Vite 빌드 결과(`static/dist/`)와 Django·unfold 정적 파일을 `STATIC_ROOT`(`staticfiles/`)로 모은다. 웹 서버(Nginx)는 이 디렉토리를 제공한다.
- 실행 시점: 배포할 때마다 `npm ci && npm run build` 다음에.
- 옵션: `--noinput`(질문 없이), `--clear`(기존 파일 삭제 후 수집).
- 감사: 기록 안 함
- 예시

  ```bash
  npm ci && npm run build
  uv run manage.py collectstatic --noinput
  ```

### `compilemessages`

- 용도: 번역 파일(`.po`)을 실행용 `.mo`로 컴파일한다. `.mo`는 저장소에 넣지 않으므로 설치와 배포 때마다 실행한다. 시스템에 `gettext`가 있어야 한다.
- 실행 시점: 배포할 때마다, 번역 파일을 고친 뒤.
- 옵션: `--locale=`(예: `ko`, `zh_Hans`, `lo`), `--ignore=.venv`.
- 감사: 기록 안 함
- 예시

  ```bash
  uv run manage.py compilemessages --ignore=.venv
  ```

### `createsuperuser`

- 용도: **사용하지 않는다.** Django 기본 슈퍼유저는 역할·권한 카탈로그와 감사를 거치지 않으므로 이 명령은 실행하면 오류(종료 코드 1)로 끝나고 `security_create_administrator`를 안내한다.
- 대신: 최초 관리자는 `security_create_administrator`로 만든다(시스템 관리자 역할 할당과 감사 기록 포함).
- 감사: 해당 없음

## 설치와 데모 (Phase 1)

### `setup_install`

- 용도: 신규 설치와 업데이트. 마이그레이션, 필수 데이터(역할 템플릿과 권한 동기화, 국가, 언어, 코드 목록 유형, 조직 단위 유형), 기관 기본 설정, 성적 척도 고정, 설치 프로파일, 최초 관리자를 차례로 처리한다. 다시 실행해도 안전하다(이미 있는 데이터와 관리자가 바꾼 값은 유지).
- 실행 시점: 최초 설치, 그리고 배포할 때마다.
- 옵션: `--institution-name=`, `--locale=`(기본 언어), `--timezone=`(예: `Asia/Seoul`), `--profile=`(설치 프로파일 키, 여러 번 지정 가능: `korean-university`, `yust-legacy`), `--grade-scale=`(성적 척도 `4.5` 또는 `4.3`. 한 번 정하면 바꿀 수 없다. 비우면 첫 프로파일의 척도), `--admin-email=`, `--admin-name=`, `--force`(질문 없이 실행. 관리자 비밀번호는 표준 입력으로 받음).
- 감사: 기록 (적용한 프로파일, 관리자 생성 여부)
- 예시

  ```bash
  uv run manage.py setup_install
  echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
      --institution-name="데모대학교" --profile=korean-university \
      --admin-email=admin@example.ac.kr --admin-name="관리자"
  ```

- 출력 해석: 단계별 `DONE`. `Administrator exists`는 시스템 관리자 할당이 이미 있어 생성을 건너뛴 것이다.
- 실패 시: 키가 없다는 오류면 `DJANGO_SECRET_KEY`와 `pii_generate_key`로 만든 값을 환경 설정에 넣는다. 마이그레이션 실패는 DB 역할 준비([설치](installation.md))를 확인한다. `The grade scale is fixed`는 이미 정해진 척도와 다른 `--grade-scale`을 준 것이다.

### `setup_demo`

- 용도: 가상 대학 데이터를 만든다(조직, 프로그램, 건물·강의실, 오늘을 기준으로 지난·현재·다음 학기와 업무 기간, 한국 대학 프로파일). 역할별 고정 데모 계정(`registrar@demo.test` 등, 비밀번호 `demo-password`)을 출력한다. 대량 데이터는 일괄 삽입으로 만든다.
- 실행 시점: 개발, 교육, 시연 환경. **운영 환경(`DJANGO_ENV=production`)에서는 `--force`를 줘도 실행되지 않는다.**
- 옵션: `--size=tiny|small|medium|large`(학생 약 20/100/2,000/20,000명. `tiny`는 테스트와 빠른 확인용), `--seed=`(같은 값이면 같은 데이터), `--force`(확인 질문 생략).
- `--student-accounts`: 재학생 전원에게 계정을 만들고 비공개 저장소의 `load-accounts.csv`(이메일, 비밀번호)에 적는다. 부하 테스트용([부하 테스트](load-testing.md)). 학적 데이터는 Phase 2부터 생기므로 그 전에는 머리글만 적힌다.
- 감사: 기록 (크기, 시드, 소요 시간)
- 예시: `uv run manage.py setup_demo --size=small --seed=42 --force`
- 실패 시: 필수 데이터가 없으면 데모 계정의 역할이 없어 건너뛴다. 먼저 `setup_install`을 실행한다. 같은 DB에서 다시 실행하면 이미 있는 데모 데이터는 건너뛴다.

## 기준정보와 학기 (Phase 1)

### `reference_import`

- 용도: 기준정보 CSV를 가져온다. 관리 화면의 **CSV 가져오기**와 같은 가져오기 규칙을 쓴다(코드로 기존 행을 찾아 갱신, 빈 번역 칸은 기존 값 유지, 실패한 행만 따로 기록).
- 인수: `type` `org_units`, `programs`, `buildings`, `rooms`, `lookup_values`, `students`(학적, Phase 2), `instructors`(교원, Phase 2), `courses`(교과목 버전, Phase 4), `registration_holds`(수강신청 제한, Phase 5) / `file` 머리글 행이 있는 UTF-8 CSV.
- 옵션: `--actor=`(필수. 가져오기 기록이 이 계정으로 남고 결과가 이 계정의 **CSV 가져오기** 화면에 보인다), `--chunk=100`(Celery 작업당 행 수), `--dry-run`(머리글 검사와 행 수만).
- 감사: 기록 (유형, 파일 이름, 행 수, 가져오기 번호, 실패 행 수)
- 열 형식: [관리자 매뉴얼 9장](../admin/09-csv-import.md).
- 종료 코드: 작업이 바로 실행되면(작업자가 동기 실행 설정이거나 행이 처리된 경우) 결과를 출력하고 실패 행이 있으면 2. 큐로 접수만 되면 0. 결과와 실패 행 CSV는 관리 화면 **기준정보 > CSV 가져오기**에서 본다.
- 예시: `uv run manage.py reference_import org_units /srv/import/org-units.csv --actor=admin@example.ac.kr --dry-run`

### `term_inspect`

- 용도: 지정 시각에 수업 중인 학기와 열려 있는 업무 기간(종류, 학기, 세션, 이름, 대상 조건, 종료 시각)을 보여 준다. 학기와 업무 기간 설정을 점검하거나 "왜 수강신청이 안 열렸는가" 같은 문의에 쓴다.
- 옵션: `--at=`(기본 현재. 예: `"2027-02-15 09:00"`. 시간대를 붙이지 않으면 서버 시간대(UTC)로 해석한다. `"2027-02-15 09:00 Asia/Seoul"` 또는 `2027-02-15T09:00+09:00`처럼 지정할 수 있다).
- 감사: 기록 안 함 (조회만)
- 출력 해석: 날짜 판단은 기관 시간대 기준이다. 계획(planned)이나 보관(archived) 상태 학기의 업무 기간은 열리지 않는다. 종료 시각은 기관 시간대로 표시한다.

## 보안 (Phase 0, 2)

### `security_create_administrator`

- 용도: 시스템 관리자 역할을 가진 계정을 만든다. 보통 `setup_install`이 호출한다.
- 옵션: `--email=`, `--name=`, `--password-stdin`(표준 입력으로 비밀번호. 비대화식 실행 시 필수).
- 감사: 기록 (생성한 사용자 ID)
- 예시: `uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="관리자"`
- 예시(비대화식): `printf '%s\n' "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="관리자" --password-stdin`
- 실패 시: `system_administrator role is missing`이면 `setup_install`를 먼저 실행한다. 비밀번호는 12자 이상이어야 한다.

### `security_sync_permissions`

- 용도: 코드의 권한 카탈로그와 DB 권한 목록을 맞춘다. 새 권한은 만들고, 카탈로그에서 빠진 권한은 삭제한다(모든 역할에서 제거됨). 시스템 역할은 항상 모든 권한을 받는다.
- 실행 시점: 배포 후(`setup_install`이 필수 데이터 단계에서 함께 처리한다).
- 옵션: `--dry-run`(생성/삭제 목록만 출력), `--force`(삭제 확인 생략).
- 감사: 기록 (생성/삭제한 권한)
- 출력 해석: `create`, `delete` 줄. 삭제가 있으면 확인 질문이 나온다.
- 실패 시: 확인 질문에 "아니요"를 고르면 종료 코드 1로 아무것도 바꾸지 않는다.

### `security_reset_mfa`

- 용도: 사용자의 2단계 인증(인증 앱, 이메일 코드, 복구 코드, 기억한 기기)을 초기화한다. 다음 로그인 때 다시 등록한다. 관리 화면에 로그인할 수 있는 관리자가 없을 때(예: 유일한 관리자가 휴대폰을 잃어버림) 쓴다. 그 밖에는 관리 화면 **사용자 > 2단계 인증 초기화**를 쓴다.
- 인수/옵션: `{user}` 사용자 이메일, `--reason=`(필수), `--actor=`(필수. 초기화를 결정한 관리자).
- 감사: 기록 (업무 감사와 보안 로그 모두. 사유 포함)
- 예시: `uv run manage.py security_reset_mfa admin@example.ac.kr --reason="휴대폰 분실, 본인 확인 완료(전화)" --actor=it-lead@example.ac.kr`

### `security_unlock_user`

- 용도: 비밀번호를 연속으로 틀려 잠긴 계정을 잠금 시간이 끝나기 전에 푼다. 관리 화면 **사용자 > 로그인 잠금 해제**와 같다.
- 인수/옵션: `{user}` 사용자 이메일, `--reason=`(필수).
- 감사: 기록 (보안 로그에도 남음)
- 출력 해석: `The account is not locked.`이면 아무것도 바꾸지 않았다.
- 참고: 잠금 기준(실패 횟수, 잠금 시간)은 관리 화면 **설정 > 로그인 수단**에서 정한다.

## 인물과 학적 (Phase 2)

### `people_find_duplicates`

- 용도: 같은 사람으로 보이는 인물 목록을 보여 준다. 기준은 주민등록번호(검색 해시)가 같거나, 로마자 성명과 생년월일이 같은 경우다. 병합된 인물은 제외한다.
- 옵션: `--limit=100`(출력할 묶음 수).
- 감사: 기록 안 함 (조회만)
- 종료 코드: 중복 후보가 있으면 2.
- 후속 조치: 각 묶음을 관리 화면 **학생과 교직원 > 인물**에서 확인하고, 같은 사람이면 남길 인물 화면에서 **중복 인물 병합**을 실행한다. 병합은 되돌릴 수 없다([관리자 매뉴얼 14장](../admin/14-merge-and-invitations.md)).
- 예시: `uv run manage.py people_find_duplicates --limit=50`

## 입학 (Phase 3)

### `admission_matriculate`

- 용도: 모집 회차의 등록 확정 지원자에게 학적을 만든다(새 학번). 관리 화면 **입학 > 지원서**의 일괄 **학적 생성**과 같다(`MatriculateApplicant`). 지원자마다 따로 처리하므로 한 명이 실패해도 나머지는 계속한다.
- 인수/옵션: `cycle` 모집 회차 코드, `--term=`(필수. 입학 학기 코드, 예: `2027-SP`. 입학일은 학기 첫날), `--actor=`(필수. `합격자 학적 생성` 권한이 있는 계정. 그 계정의 권한 범위 안의 지원자만 처리), `--dry-run`(대상 목록만).
- 감사: 기록 (회차, 학기, 대상 수, 생성 수, 실패한 수험 번호). 지원자별로 업무 감사(`application.matriculated`)도 남는다.
- 종료 코드: 회차나 학기 코드가 없거나 `--actor`가 없으면 1, 실패한 지원자가 있으면 2.
- 예시: `uv run manage.py admission_matriculate DEMO-2027-REG --term=2027-SP --actor=admissions@example.ac.kr --dry-run`
- 실패 시: `Only accepted offers without a student record ...`는 이미 학적이 있거나 등록 확정 상태가 아닌 경우, `The program is not in effect on the admission date.`는 입학일에 프로그램이 유효하지 않은 경우다(기준정보 > 프로그램의 적용 기간 확인). `not in your scope`는 `--actor` 계정의 권한 범위 밖이다.

### `admission_expire_drafts`

- 용도: 마감된 회차의 작성 중 지원서와, 설정한 기간(**설정 > 입학 > 작성 중 지원서 만료(일)**, 기본 90일) 동안 고치지 않은 작성 중 지원서를 **기한 만료**로 바꾼다. 만료된 지원서는 같은 회차의 새 지원을 막지 않는다.
- 실행 시점: 스케줄(매일 03:10, Celery beat 작업 `admission.expire_drafts`가 이 명령을 실행).
- 옵션: `--dry-run`(대상 수만).
- 감사: 기록 (만료한 수)
- 예시: `uv run manage.py admission_expire_drafts --dry-run`

## 개설강좌 (Phase 4)

### `section_copy`

- 용도: 이전 학기의 개설강좌로 새 학기 편성을 시작한다. 관리 화면 **개설강좌 > 다른 학기에서 복사**와 같다(`CopySections`). 폐강되지 않은 강좌를 작성 중 상태로 복사하고, 담당 교원(재직 중인 경우), 강의 시간과 강의실, 좌석 할당(전환 시각은 학기 시작일 차이만큼 이동), 강의계획서(비공개 초안)를 함께 복사한다. 교과목 버전은 새 세션 시작일에 유효한 버전으로 바뀐다.
- 인수/옵션: `from-term`, `to-term` 학기 코드(예: `2026-FA`), `--org-unit=`(이 조직 코드의 강좌만, 여러 번 지정 가능), `--dry-run`(복사를 트랜잭션 안에서 해 보고 되돌린다. 결과는 실제와 같다), `--actor=`(필수. 그 계정의 `개설강좌 편성` 권한 범위 안의 강좌만 복사).
- 감사: 기록 (원본·대상 학기, 복사, 건너뜀, 확인 필요 건수. 실제 복사는 업무 감사 `sections.copied`도 남는다)
- 출력 해석: `skipped`는 대상 학기에 같은 분반이 이미 있거나 유효한 교과목 버전이 없는 강좌, `note`는 복사했지만 빠진 것(강의실이 이미 사용 중이라 강의실 없이 복사, 퇴직한 교원 등)이다. 세션은 코드로 맞추고, 없으면 전체 학기 세션에 넣는다.
- 종료 코드: 학기 코드가 없거나 `--actor`가 없으면 1.
- 예시: `uv run manage.py section_copy 2026-FA 2027-FA --actor=academic@example.ac.kr --dry-run`

### `schedule_check_conflicts`

- 용도: 시간표를 공개하기 전에 학기 개설강좌를 점검한다. 강의실·교원 중복 배정은 DB가 이미 막지만, 다음처럼 DB가 허용하는 문제를 찾는다: 강의실 수용 인원보다 큰 정원, 세션 시작일에 유효하지 않은 교과목 버전, 퇴직한 담당 교원, 정원을 넘는 좌석 할당, 세션 밖의 강의 날짜. 백업 복원처럼 제약 없이 들어온 데이터의 강의실 중복도 확인한다.
- 인수: `term` 학기 코드.
- 감사: 기록 안 함 (조회만)
- 종료 코드: 문제가 있으면 2, 학기 코드가 없으면 1. 담당 교원이나 강의실, 강의 시간이 아직 없는 강좌는 참고(`Note`)로만 보여 준다.
- 예시: `uv run manage.py schedule_check_conflicts 2027-SP`

## 수강신청 (Phase 5)

### `registration_preflight`

- 용도: 수강신청을 열기 전에 학기를 점검한다. 수강신청·수강 정정 기간, 규칙 세트, 공개 강좌 수, 정원 0인 강좌, 정원을 넘는 좌석 할당, 세션 시작일에 유효하지 않은 교과목 버전, 학점 상한이 적용되지 않는 재학생 수, 수강신청 제한이 걸린 학생 수를 보여 준다.
- 인수: `term` 학기 코드(예: `2027-SP`).
- 감사: 기록 안 함 (조회만)
- 종료 코드: 문제가 있으면 2. 규칙 세트가 없으면 문제가 아니라 참고로 보여 준다(규칙 기본값 적용).
- 예시: `uv run manage.py registration_preflight 2027-SP`

### `registration_simulate`

- 용도: 학생이 지금(또는 지정 시각에) 강좌를 신청하면 어떻게 되는지 규칙별 결과를 보여 준다. 저장하지 않고 시도 기록도 남기지 않는다. "왜 신청이 안 되나요?" 문의에 쓴다.
- 인수: `student-number` 학번, `section` `과목코드-분반`(예: `CSE2010-01`).
- 옵션: `--term=`(학기 코드. 기본은 그 분반이 있는 가장 최근 학기), `--at=`(판단 시각. 예: `"2027-02-10 10:00 Asia/Seoul"`).
- 감사: 기록 안 함 (조회만)
- 출력 해석: 규칙마다 통과/실패, 차단/경고, 메시지. 예외(override)가 적용된 규칙은 실패로 보이지만 차단하지 않는다. 정원은 규칙 표 아래에 따로 나온다.
- 종료 코드: 신청이 거절될 상황이면 2.
- 예시: `uv run manage.py registration_simulate 202612345 CSE2010-01 --at="2027-02-10 10:00 Asia/Seoul"`

### `waitlist_promote`

- 용도: 빈자리가 있는 강좌의 대기자를 순서대로 신청 처리한다. 승격 때 모든 규칙을 다시 확인하고, 규칙을 통과하지 못한 대기자는 대기에서 제외(사유 기록)한다. 수강신청·수강 정정 기간이 모두 닫힌 강좌의 대기는 만료한다. 학생에게 결과 메일을 보낸다.
- 인수/옵션: `term?` 학기 코드(기본: 대기자가 있는 모든 학기), `--actor=`.
- 감사: 기록 (강좌 수, 승격, 제외, 만료 수)
- 실행 시점: 취소·철회와 좌석 할당 해제 때 해당 강좌만 큐 작업으로 즉시 처리된다. 이 명령은 매시간 스케줄로 빠진 것을 처리하는 안전망이다.
- 예시: `uv run manage.py waitlist_promote 2027-SP --actor=registrar@example.ac.kr`

### `registration_release_reserved_seats`

- 용도: 전환 시각이 지난 좌석 할당(예: 전공자 유보석)을 처리 완료로 표시하고 그 강좌의 대기자 승격 작업을 큐에 넣는다. 유보석은 전환 시각이 지나면 계산상 바로 일반석이 되므로, 이 명령은 대기자에게 자리를 넘기는 역할만 한다.
- 감사: 기록 안 함 (5분마다 실행. 승격 결과는 수강신청 기록에 남는다)
- 실행 시점: 스케줄(5분마다, Celery beat 작업 `registration.release_reserved_seats`). 승격 작업은 강좌별 `registration.promote_waitlist`(Redis 잠금으로 한 강좌에 하나씩).
- 예시: `uv run manage.py registration_release_reserved_seats`

## 성적 (Phase 6)

### `term_close`

- 용도: 학기를 마감한다. 학기의 모든 성적이 확정되어 있어야 한다. 학생 묶음(100명)마다 학기 기록(학점, 학기·누적 평점)을 계산하고 학업 상태(정상, 학사경고, 제적 검토)와 성적우수 해당 여부를 판정한 뒤(Celery chord의 `grading.close_term_records` 작업), 마무리 작업 `grading.finish_term_close`가 프로그램별 성적우수 순위를 매기고 학기 기록을 공식 기록으로 마감하고 학기를 **성적 마감** 상태로 바꾼다. 진행률은 `job_batches`에 남고 **성적 > 학기 기록** 화면 위에 보인다. 끝나면 시작한 직원에게 메일을 보낸다. 관리 화면 **성적 > 학기 기록 > 학기 마감**과 같다.
- 인수/옵션: `term` 학기 코드, `--dry-run`(마감할 수 있는지만 확인), `--reason=`(기록에 남길 사유), `--actor=`.
- 감사: 기록 (학생 수, 미확정 강좌 수, 배치 ID). 마감이 끝나면 `term.closed` 감사 기록에 학사경고, 제적 검토, 성적우수 인원이 남는다.
- 종료 코드: 확정되지 않은 성적이 있는 강좌가 있으면 2(강좌별 미확정 건수 출력). 공개(published) 상태가 아닌 학기는 1.
- 실행 시점: 성적 입력·확정이 끝난 뒤. 배치 진행은 Flower와 학기 기록 화면에서 본다. Celery 워커가 없으면 학기 상태가 바뀌지 않는다. 묶음 하나가 DB 오류로 실패하면 3번까지 다시 시도하고, 그래도 실패하면 배치가 실패로 남고 학기는 바뀌지 않는다(원인을 고친 뒤 다시 실행한다. 다시 실행해도 결과가 같다).
- 예시: `uv run manage.py term_close 2026-FA --dry-run`, `uv run manage.py term_close 2026-FA --reason="2026-2 성적 마감" --actor=registrar@example.ac.kr`

### `grades_recalculate`

- 용도: 확정 성적으로 학기 기록(학점, 학기·누적 평점)을 다시 계산한다. 성적 처리 정책(평점 자릿수, 재수강 반영)을 바꾼 뒤 지난 학기에 적용할 때 쓴다. 학업 상태와 성적우수는 학기 마감 때 정한 값을 유지한다. 성적 정정 승인은 그 학생을 자동으로 다시 계산하므로 이 명령이 필요 없다.
- 옵션: `--term=`(그 학기에 성적이 있는 학생을 그 학기부터), `--student-number=`(한 학생), `--reason=`(필수), `--actor=`.
- 감사: 기록 (학생 수, 사유)
- 종료 코드: 사유가 없거나 학기 코드·학번을 찾지 못하면 1.
- 예시: `uv run manage.py grades_recalculate --term=2026-SP --reason="평점 소수 셋째 자리로 변경"`

### `grades_remind_missing`

- 용도: 아직 성적을 제출하지 않은 강좌(미입력 또는 임시 저장)의 담당 교원에게 안내 메일을 보낸다. 교원별로 강좌를 묶어 한 통씩 보낸다.
- 인수/옵션: `term` 학기 코드, `--dry-run`(보내지 않고 대상만 출력), `--actor=`.
- 감사: 기록 (강좌 수, 교원 수, 보낸 수)
- 실행 시점: 성적 입력 기간 마감 며칠 전. 필요하면 스케줄에 등록한다.
- 예시: `uv run manage.py grades_remind_missing 2026-FA --dry-run`

## 강의평가 (Phase 7)

## 증명서 (Phase 8)

## 어학/종합시험 (Phase 9)

## 출석 (Phase 10)

## 졸업 (Phase 11)

## LMS 연동 (Phase 12)

## 운영 점검과 정리 (Phase 13)

### `audit_seal`

- 용도: 감사 테이블(`audit.record_changes`, `audit.activity_log`, `audit.security_events`)의 새 행을 해시 체인에 잇는다([감사 무결성](audit-and-maintenance.md)). 스키마 소유자 연결(`migrator`)로 실행된다.
- 옵션: `--table=`(record_changes, activity_log, security_events 중 선택, 여러 번), `--actor=`.
- 감사: 기록 (테이블별 봉인 수)
- 실행 시점: 매일 03:30 스케줄.
- 예시

  ```bash
  uv run manage.py audit_seal
  uv run manage.py audit_seal --table=activity_log
  ```

### `audit_verify_chain`

- 용도: 감사 행의 내용 해시와 체인을 다시 계산해 변조·삭제·순서 변경을 찾는다. 테이블마다 검사 수, 봉인 수, 불일치 수와 첫 불일치 id를 출력한다.
- 옵션: `--table=`.
- 감사: 없음 (조회)
- 종료 코드: 불일치가 있으면 2.
- 실행 시점: 백업 전, 보안 점검, 정리 뒤.

### `audit_prune`

- 용도: 보존 기간이 지난 **봉인된** 감사 행을 지운다. 스키마 소유자 연결로, `app.audit_maintenance = on`을 켠 트랜잭션 안에서 실행된다. 봉인되지 않은 행은 남긴다(먼저 `audit_seal`). 지울 때마다 보안 이벤트 `audit.pruned`(테이블, 기준일, 삭제 수, id 범위, 경계 행의 `chain_hash`)를 남긴다.
- 옵션: `--before=YYYY-MM-DD`(필수, 그날 0시 이전), `--table=`, `--dry-run`(건수만), `--actor=`.
- 감사: 기록 (기준일, 테이블별 삭제 수와 id 범위)
- 실행 시점: 보존 정책에 따라, 백업 뒤.
- 예시

  ```bash
  uv run manage.py audit_prune --before=2023-03-01 --dry-run
  uv run manage.py audit_prune --before=2023-03-01 --table=record_changes --actor=ops@example.ac.kr
  ```

### `media_prune_orphans`

- 용도: 소유자가 사라진 미디어 행과 행이 없는 디렉터리(`<media id>/`)를 비공개 저장소에서 지운다(인물 사진, 지원 서류, 증명서 PDF, 시험 증빙).
- 옵션: `--dry-run`(목록만), `--actor=`.
- 감사: 기록 (행 수, 디렉터리 수)
- 실행 시점: 월 1회 또는 대량 삭제 뒤.

## 개인정보 암호화 키 (Phase 0)

### `pii_generate_key`

- 용도: `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`에 넣을 새 키(32바이트, `base64:...`)를 출력한다. 아무것도 저장하지 않는다.
- 감사: 기록 안 함
- 주의: `PII_HASH_KEY`를 바꾸면 모든 검색 해시(`*_hash`)가 무효가 된다. 암호화 키만 교체한다: 이전 키를 `PII_PREVIOUS_KEYS`로 옮기고 `pii_reencrypt`를 실행한다.
- 예시

  ```bash
  uv run manage.py pii_generate_key
  ```

### `pii_reencrypt`

- 용도: 키 교체 후 이전 키로 암호화된 개인정보를 현재 키로 다시 암호화한다. 레코드를 나눠 Celery 작업 묶음(group)으로 실행한다. 이미 현재 키인 레코드는 건드리지 않는다.
- 인수: 암호화 개인정보 필드가 있는 모델(`app_label.Model`, 예: `person.Person`).
- 옵션: `--chunk=500`(작업당 레코드 수), `--dry-run`(이전 키를 쓰는 레코드 수만 셈), `--force`(확인 없이), `--actor=`.
- 감사: 기록 (배치 ID, 작업 수 / 미리보기 건수)
- 확인: Flower에서 작업 진행을 본다. 끝난 뒤 `--dry-run` 결과가 0이면 이전 키를 `PII_PREVIOUS_KEYS`에서 뺀다.
- 예시

  ```bash
  uv run manage.py pii_reencrypt person.Person --dry-run
  uv run manage.py pii_reencrypt person.Person --force --actor=ops@example.ac.kr
  ```

## 다국어 (Phase 0)

### `i18n_missing`

- 용도: 소스에서 번역 대상 문자열을 `makemessages`와 같은 방식으로 추출해(파일은 쓰지 않음) 모든 카탈로그(전역 `locale/`, 앱별 `locale/`)와 비교하고, 언어별로 누락(카탈로그에 없음, 빈 `msgstr`, fuzzy, 자리표시자 불일치)과 더 이상 쓰지 않는 항목(obsolete)을 보여 준다.
- 인수/옵션: `[locale]`(한 언어만, 예: `ko`, `zh-hans`, `lo`), `--strict`(누락이 있으면 종료 코드 2. CI에서 사용), `--no-extract`(소스 추출 없이 카탈로그만 검사).
- 감사: 기록 안 함
- 필요: GNU gettext(`xgettext`, `msguniq`).
- 예시

  ```bash
  uv run manage.py i18n_missing --strict
  uv run manage.py i18n_missing lo
  ```

### `i18n_export`

- 용도: 번역가에게 줄 표(`.xlsx` 또는 `.csv`, 확장자로 결정)를 만든다. 열: `catalog`(카탈로그 위치), `context`, `source`(영문 msgid), `source_plural`, `translation`, `note`(원본 키).
- 인수/옵션: `{locale} {path}`, `--missing`(번역이 없는 문자열만).
- 감사: 기록 안 함
- 예시: `uv run manage.py i18n_export ko storage/ko.xlsx --missing`

### `i18n_import`

- 용도: 번역가가 채운 표를 카탈로그(`.po`)에 반영하고 컴파일(`.mo`)한다. 카탈로그에 있는 문자열(카탈로그, 문맥, 영문이 일치)만 가져오고 빈 번역은 무시한다.
- 인수/옵션: `{locale} {path}`, `--dry-run`(쓸 문자열 목록만 출력), `--actor=`.
- 감사: 기록 (언어, 번역 수)
- 주의: 카탈로그는 저장소에서 관리한다. 가져온 뒤 `.po` 변경 내용을 커밋한다.

### `i18n_makemessages`

- 용도: 저장소 루트에서 `makemessages`를 실행해 모든 카탈로그를 소스에 맞춘다(ko, zh_Hans, lo). 앱에 `locale/`이 있으면 그 앱 카탈로그에, 없으면 전역 `locale/`에 쓴다. `.venv`, `tests`, `docs` 등은 건너뛴다.
- 옵션: Django `makemessages`와 같다(`-l`, `--no-obsolete` 등).
- 감사: 기록 안 함
- 예시: `uv run manage.py i18n_makemessages`

## 점검 (Phase 0)

### `pdf_sample`

- 용도: 한국어, 중국어, 라오어, 영어가 섞인 표를 PDF로 렌더링해 글꼴과 PDF 서비스(Gotenberg) 연결을 점검한다.
- 인수: `[path]`(기본 `pdf-sample.pdf`, 비공개 파일 저장소 `PRIVATE_MEDIA_ROOT` 기준).
- 감사: 기록 안 함
- 실패 시: 종료 코드 1. 연결 오류면 `GOTENBERG_URL`, `GOTENBERG_TIMEOUT`과 Gotenberg 컨테이너 상태를 확인한다.
- 예시: `uv run manage.py pdf_sample`

### `naming_check`

- 용도: DB 스키마와 소스를 [명명 규칙](../../../development/naming.md)으로 검사한다. 검사 대상은 실제 DB 카탈로그의 테이블·컬럼 이름(`public`, `audit`, `reporting` 스키마), Ninefruits 앱의 마이그레이션 파일 이름, 관리 명령 이름(`context_action`), 번역 카탈로그(`.po`)의 msgid·msgctxt다.
- 규칙: snake_case, 금지 접미사(`_old`, `_new`, `_backup`, `_tmp`, 날짜, 숫자), 언어 코드가 들어간 이름, 시간대 없는 시각 컬럼(`timestamp without time zone`), 불리언 컬럼 이름(`is_`, `has_`, `can_` 또는 동사형), 날짜 컬럼 이름(`_date`), 의미 키 형태의 msgid(`registration.errors.x`). Django·패키지가 정한 테이블(`django_*`, allauth, Celery beat, `settings`, `cache`, `jobs`, `media` 등)은 제외한다.
- 옵션: `--database=`(검사할 DB 연결, 기본 `default`), `--skip-database`(DB 없이 파일 검사만).
- 감사: 기록 안 함
- 종료 코드: 문제가 있으면 2.
- 예시

  ```bash
  uv run manage.py naming_check
  ```
