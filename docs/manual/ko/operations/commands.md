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
- 인수: `type` `org_units`, `programs`, `buildings`, `rooms`, `lookup_values`(학생·교원·교과목·수강 제한은 해당 Phase에서 추가) / `file` 머리글 행이 있는 UTF-8 CSV.
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

## 입학 (Phase 3)

## 개설강좌 (Phase 4)

## 수강신청 (Phase 5)

## 성적 (Phase 6)

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
