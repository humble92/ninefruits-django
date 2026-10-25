# Phase 13 안정화와 배포 결과 보고

- 작성일: 2026-10-25
- 대상: 개발팀, 프로젝트 관리자, 운영 담당자
- 관련: [이식 계획 14절 Phase 13](porting-plan.md#phase-13-안정화와-배포-m), 원본 [Phase 13 보고](https://github.com/humble92/ninefruits-laravel/blob/main/porting/phase-13-report.md), [보안 점검](security-review.md), [배포 체크리스트](../docs/manual/ko/operations/deployment-checklist.md), [부하 테스트](../docs/manual/ko/operations/load-testing.md), [키 관리](../docs/manual/ko/operations/security-keys.md)

## 1. 요약

새 기능 없이 이식 결과를 원본과 대조하고 운영 준비를 마쳤다.

- **스키마 동등성 전체 검증**(`pg_dump --schema-only`): 원본 객체 1,253개가 모두 같다. Django 쪽에만 있는 것은 프레임워크 테이블 객체 112개(`django_*`, `auth_*`, allauth, knox), 원본에만 있는 것은 Laravel `migrations` 테이블 객체 5개뿐이다(2절).
- **보고서 CSV 대조**: 원본 데모 DB의 데이터를 Django DB에 그대로 복원하고 표준 보고서 7종을 11개 조건으로 양쪽에서 뽑았다. 689행이 칸 단위로 모두 같다(3절).
- **부하 테스트**(Locust, 대용량 데모): HTTP 실패 0, 초과 등록 0. 대용량 데모 생성은 **416초**(원본 약 65분). 화면 p95 기준은 공유 개발 머신(4 vCPU)의 100 VU에서 맞추지 못했다(4절).
- **보안 점검**: 원본 5.1절 12건 모두 구현·테스트, Django 고유 발견 4건(F1~F4) 고침. mypy strict 오류 0(시작 675건, CI 차단 전환), bandit 중간 이상 0, pip-audit 취약점 0(5절).
- **문서**: 운영 매뉴얼 9편, 관리자 매뉴얼 28장, README, 스크린샷(4개 언어 × 3장)을 Django 기준으로 정리했다(6절).
- **코디네이터 수정**: 이식되지 않았던 운영 명령 `system_health_check`(원본 `system:health-check`, 12개 점검), 예약된 감사 봉인이 실제로는 돌지 않던 버그, SMTP 인증·암호화 설정 누락, 관리 대시보드 앱 제목 미번역, 세션 유휴 만료, `setup_demo` 선행 조건 안내(7절).

수치

- 테스트 **1,090개** 통과(`-m "not concurrency"` 1,089개 2분 14초 + 동시성 1개). 원본은 463개(이 작업 환경에서 오라클로 돌리면 455개 통과, 8개는 원본 쪽에서 실패하며 Django 이식과 무관). 테스트 파일 118개, 대응표 `porting/test-mapping.md`의 원본 파일 76개 모두 대응(완료 71, 부분 5: 다른 Phase 테스트에 나뉘어 있거나 화면 대신 동작 단위로 옮긴 것).
- ruff format·lint, raw SQL 검사, `makemigrations --check`, `i18n_missing --strict`(ko·zh_Hans·lo 누락 0), `manage.py check`, mypy strict(713개 파일) 모두 통과.
- 빈 DB에서 `setup_install --force --profile=korean-university --grade-scale=4.5` 2초, `setup_demo --size=small --seed=42 --force` 16초(원본 35초).
- 관리 명령 53개, 모두 운영 매뉴얼 `commands.md` 4개 언어에 있다(테스트로 강제).

## 2. 스키마 동등성 전체 검증

`tools/schema_dump_diff.py`는 두 `pg_dump --schema-only --no-owner --no-privileges` 결과를 객체(`-- Name: ...; Type: ...; Schema: ...` 머리) 단위로 나눠 본문을 비교한다. 프레임워크 테이블 객체와 Laravel `migrations` 테이블은 예상된 차이로 따로 센다.

| 항목 | 개수 |
|---|---|
| 비교한 원본 객체(테이블, 칼럼 정의, 제약, 인덱스, 함수 30개, 트리거, RLS 정책, reporting 뷰 8개, 시퀀스) | 1,253 |
| 본문이 같은 객체 | 1,253 |
| Django에만 있는 프레임워크 객체 | 112 |
| 원본에만 있는 객체(Laravel `migrations`) | 5 |
| 문제 | 0 |

도구가 차이를 잡는지는 칼럼 타입을 바꾼 덤프로 확인했다(109건 보고, 종료 코드 1). 상시 검사는 기존 카탈로그 지문 테스트(`tests/db/test_schema_equivalence.py`)와 모델·표 대조(`tests/db/test_model_schema.py`)가 맡는다.

재현:

```bash
pg_dump --schema-only --no-owner --no-privileges <db> > /tmp/django-schema.sql
uv run python tools/schema_dump_diff.py /tmp/django-schema.sql
```

## 3. 보고서 CSV 대조

같은 시드라도 PHP Faker와 Python Faker가 만드는 데이터는 다르므로, 데이터를 맞춰 놓고 코드만 비교했다.

1. 원본 small 데모 DB(`laravel_demo`, 학생 기록 104, 수강 723)를 `pg_dump --data-only`(Laravel `migrations` 제외)로 뜬다.
2. 빈 Django DB를 마이그레이션하고 업무 테이블을 비운 뒤 `session_replication_role = replica`로 복원한다(트리거·FK 검사 없이 그대로).
3. 원본은 `ReportCatalog::csv()`를, Django는 `tools/report_csv_dump.py`(`ReportCatalog.csv()`)를 같은 조건으로 실행한다. 영어, 시스템 수행자.

| 보고서(조건) | 행 | 결과 |
|---|---|---|
| students / students(status=enrolled) | 104 / 63 | 같음 |
| headcount | 36 | 같음 |
| term_records / term_records(term=1) | 64 / 64 | 같음 |
| graduation_candidates | 33 | 같음 |
| status_changes | 5 | 같음 |
| section_enrollments / section_enrollments(term=2) | 203 / 52 | 같음(행 순서까지) |
| not_registered(term=2) / not_registered(term=3) | 3 / 61 | 같음 |

CSV로 파싱한 값이 모두 같다. 바이트로는 따옴표 방식만 다르다(PHP `fputcsv`는 공백이 있는 칸을 따옴표로 감싸고, Python `csv`는 필요할 때만 감싼다. 둘 다 RFC 4180이고 엑셀에서 같게 열린다). 처음 비교에서 시각 칸이 원본(`2026-10-24 07:26:59+00`, PostgreSQL 텍스트)과 달라 p11이 `cell()`을 원본 형식으로 맞췄다.

## 4. 부하 테스트

p13-load 측정(2026-10-24). 4 vCPU 개발 머신(Xeon 2.1GHz, `nproc`=4, RAM 15GB)을 다른 작업과 같이 썼고 측정 중 load average는 7~21이었다. Locust, gunicorn, PostgreSQL 18, Redis가 모두 같은 머신에서 돌았으므로 수치는 하한선이다.

- 데모 `--size=large --seed=42 --student-accounts`: **416초**(학생 20,004명, 학생 계정 11,437개). 원본은 약 65분이었고, 수강·성적 시더를 대량 삽입으로 바꾼 결과다(Phase 5·6).
- 2027년 봄학기 수강신청을 전 학년에 열었고 공개 분반은 52개(정원 2,262)다.
- 시나리오는 원본 k6와 같다: 로그인 → 수강신청 화면 → 검색(HTMX) → 등록 → 취소. 반복마다 다른 학생이다(`loadtest/registration.py`, 실행 도구 `loadtest/run.sh`, 좌석 점검 `loadtest/seat_check.sql`).
- 학생마다 다른 `X-Forwarded-For`를 보내고 `TRUSTED_PROXY_COUNT=1`로 돌렸다(실제 캠퍼스와 같은 조건).

| 조건 (1분) | req/s | 화면 p95 | 등록 p95 | 실패 | 등록 성공/거절 | PG 연결 최대 |
|---|---|---|---|---|---|---|
| 2 VU, 워커 9, 풀 없음 | 5.1 | 200ms | 640ms | 0/300 | 50/0 | 3 |
| 2 VU, 워커 9, 풀+준비된 문장 | 6.2 | 160ms | 470ms | 0/372 | 62/0 | 22 |
| 100 VU, 워커 4, 풀 없음 | 16.8 | 6.0s | 11s | 0/1,005 | 52/86 | 6 |
| 100 VU, 워커 16, 풀 없음 | 17.1 | 6.1s | 11s | 0/1,027 | 60/86 | 18 |
| 100 VU, 워커 4, 풀+준비된 문장 | 25.6 | 4.1s | 7.0s | 0/1,536 | 97/155 | 12 |
| 100 VU, 워커 9, 풀+준비된 문장 | 25.4 | 4.5s | 7.3s | 0/1,523 | 77/167 | 22 |
| 100 VU, 워커 16, 풀+준비된 문장 | 23.4 | 4.6s | 8.4s | 0/1,405 | 131/79 | 36 |
| 200 VU, 워커 9, 풀+준비된 문장 | 29.8 | 9.4s | 14s | 0/1,792 | 66/172 | 22 |
| 200 VU, 워커 16, 풀+준비된 문장 | 29.2 | 9.1s | 14s | 0/1,761 | 53/174 | 36 |
| 100 VU, 한 주소(NAT), 기본 30/m/ip | (429 위주) | 2.0s | 3.3s | 4,846/9,862 | 20/10 | 22 |

읽는 법

- 처리량은 CPU에 묶였다. 워커 4·9·16개의 처리량이 같고 연결과 잠금 대기만 늘었다. 100 VU의 수 초 지연은 요청 대기열이다.
- RLS 때문에 쿼리 **계획 수립**이 DB 시간의 대부분이다(수강신청 화면: 쿼리 31개, 계획 51ms, 실행 19ms). 연결 풀과 준비된 문장(`DB_PREPARE_THRESHOLD=2`)으로 처리량이 약 50% 늘었다.
- 등록 거절은 만석(`capacity`)과 중복 교과목(`duplicate_course`)으로 정상 동작이다. 잠금 대기는 같은 분반의 좌석 잠금에서만 짧게 생겼다(순간 최대 1~12건). 모든 측정에서 초과 등록 0, HTTP 실패 0이다(한 주소 측정 제외).
- 원본(Sail 내장 서버, 노트북)의 100 VU·워커 16 수치는 34.5 req/s, 화면 p95 4.33s였다. 장비가 달라 직접 비교는 어렵지만 같은 규모이고, 둘 다 원인은 앱 서버 CPU다.

개선한 것

- 대기자 위치 계산의 N+1 제거(`waitlists.positions()`, 대기 항목마다 3개 → 1개). 쿼리 수 테스트 `tests/registration/test_portal_query_count.py`.
- 좌석 잠금을 `FOR NO KEY UPDATE OF sections`로 바꿨다. 수강 시도·LMS 기록의 FK 검사가 잠금에 막히지 않고, 잠금 중 쿼리가 하나 줄었다.
- `DB_PREPARE_THRESHOLD`(기본 0 = 끔) 설정, `config/gunicorn.py`(sync 워커, `GUNICORN_*` 환경 변수, 기본 워커 = 코어×2+1). Dockerfile이 이를 쓴다.

결정

- gunicorn sync 워커는 코어×2+1을 넘기지 않는다.
- `DB_POOL=true`, `DB_POOL_MIN=1`, `DB_POOL_MAX=2`, `DB_PREPARE_THRESHOLD=2`.
- ASGI는 도입하지 않는다(원본의 Octane 보류와 같은 판단: 동기 뷰, 처리량이 CPU에 비례).
- 운영 전 전용 스테이징(앱 서버와 DB 분리)에서 200·500 VU로 기준(화면 p95 < 800ms, 등록 p95 < 1.5s, 실패 < 1%)을 다시 확인한다. 이번 환경에서는 **기준 미충족**이다.

배포 발견: 기본 `LOGIN_RATE_LIMIT_PER_IP=30/m/ip`에서 학교 전체가 한 주소(NAT, 또는 `TRUSTED_PROXY_COUNT=0`인 Nginx 뒤)로 보이면 로그인이 학교 전체에서 분당 30건이다. 측정에서 로그인 4,876건 중 30건만 성공했다. 5절 F1.

## 5. 보안 점검

p13-sec 결과. 상세는 [security-review.md](security-review.md).

원본 5.1의 12건(H1·H3·H4·H5·M1·M6·M7·M8·L1·L2·L4·L5)은 모두 Django에 구현되어 있고 테스트로 확인했다. 이번에 보강한 테스트는 H1 화면, H5 행위자 검사, M8 관리 화면, L1 헤더 액션, L5 CSV 크기 5건이고, 원본 HardeningTest는 오라클로 6/6 통과했다.

5.2 후속 과제:

- M5(IP 단위 로그인 제한)와 다운로드 `nosniff`는 allauth/Django 기본 기능으로 해결되었다.
- H2·M2·M3·M4·M9와 메일·데모 비밀번호는 원본과 같은 수준으로 남는다.
- L3 CSP는 nonce로 부분 해결했다.

Django 고유 발견:

| 번호 | 내용 | 조치 |
|---|---|---|
| F1 | allauth가 원본에 없던 IP 단위 로그인 제한(분당 30)을 더하는데, 앱이 프록시 뒤에서도 `REMOTE_ADDR`만 봐서 Nginx 뒤에서는 학교 전체 로그인이 분당 30건으로 묶였다 | `ninefruits.core.http.client_ip`(`X-Forwarded-For`를 오른쪽부터 `TRUSTED_PROXY_COUNT`개 신뢰), 감사·모든 rate limit이 같은 함수를 쓴다. `LOGIN_RATE_LIMIT_PER_IP`로 조정. NAT 캠퍼스는 올려야 하지만 그만큼 계정을 번갈아 시도하는 공격을 덜 막는다(배포 체크리스트에 기록) |
| F2 | `DJANGO_SECRET_KEY`를 바꾸면 TOTP 비밀값·복구 코드·SSO 클라이언트 비밀을 읽을 수 없게 된다(그 키에서 파생한 키로 암호화) | `DJANGO_SECRET_KEY_FALLBACKS`, 복호화는 이전 키도 시도, `security_reencrypt_secrets`(dry-run, 감사), 키 관리 문서 4개 언어 |
| F3 | 세션이 유휴가 아니라 로그인 시각 기준 120분에 끝났다(원본은 마지막 요청 기준). 성적 입력 중 로그아웃될 수 있었다 | 7절 |
| F4 | 기준정보·인물 CSV 가져오기에 크기 제한이 없었다 | 12 MB 제한(원본 Livewire 업로드 한도) |

정적 검사: mypy strict 오류 0(시작 675건, CI에서 차단으로 전환), bandit 중간 이상 0(오탐 3건은 사유와 함께 `# nosec`), pip-audit 취약점 0(164개 패키지). `gettext as gettext_now` 별칭은 `makemessages`가 추출하지 못해 일반 `gettext`로 바꿨고, 같은 별칭이 다시 생기면 실패하는 테스트(`tests/i18n/test_translation_aliases.py`)를 넣었다.

## 6. 문서와 다국어

p13-docs 결과. 문서는 원본 6절과 같은 구성으로 정리했다.

- **운영 매뉴얼:** 9편 가운데 6편을 Django 기준으로 4개 언어 모두 새로 썼다. 설치, 배포 체크리스트, 백업·복구, 장애 대응, 예약 작업, 감사와 정리이며, gunicorn+Nginx, Celery worker와 단일 beat, `setup_install`, `/api/v1/health/`, `TRUSTED_PROXY_COUNT`·`LOGIN_RATE_LIMIT_PER_IP`를 반영했다. 키 관리는 p13-sec, 부하 테스트는 p13-load가 썼고 명령 레퍼런스는 각 Phase가 채웠다.
- **관리자 매뉴얼:** 1~25장의 "Phase N에서 추가" 문구를 장 링크로 바꿨다. 26~28장은 Phase 11·12에서 썼다. 화면 이름은 각 언어의 실제 UI 라벨(`.po`)에 맞췄다.
- **README:** 영어판(`README.md`)을 기본으로 하고 한국어(`README.ko.md`)·중국어·라오어판을 두었다. `README.en.md`는 `README.md`를 가리키는 두 줄짜리 안내로 남겼다.
- **스크린샷:** `tools/screenshots.py`(Playwright, Chromium)로 데모 DB(`setup_demo --size=small --seed=42`)에서 찍었다. 원본과 같은 3개 화면(최고관리자 `/admin/`, 교수·학생 `/portal/`)을 4개 언어로 1366×900에 찍어 `docs/screenshots/{en,ko,zh_Hans,lo}/`에 넣었다(12장, 716KB). 포털 화면은 원본과 거의 같다. 관리 화면은 unfold 대시보드라 원본과 모양이 다르다. 앱 제목이 번역되지 않던 문제를 7절에서 고친 뒤 코디네이터가 새 데모 DB에서 12장을 다시 찍었다.
- **언어 추가 가이드:** 각 절차를 코드와 대조했고 스크린샷 절차를 넣었다.
- 원어민 검수는 여전히 남은 일이다.

## 7. 코디네이터 수정

에이전트 결과를 검토하며 직접 고친 것.

| 내용 | 원인과 수정 | 테스트 |
|---|---|---|
| 운영 명령 `system_health_check`가 없었다(원본 `system:health-check`, 대응표에 "Phase 13"으로 남아 있었다) | 같은 12개 점검(Horizon 대신 Celery 워커 ping, 스케줄러 대신 beat 심장박동), `--json`, 실패 시 종료 코드 2. 명령 레퍼런스·배포 체크리스트·감사와 유지보수 4개 언어 | `tests/tooling/test_system_health_check.py`(원본 `OperationsCommandsTest` 사례) |
| 매일 03:30 감사 봉인이 돌지 않았다 | beat 일정이 `audit.seal` 작업을 부르지만 그런 작업이 등록되어 있지 않았다. `ninefruits/audit/tasks.py` 추가 | 일정의 모든 작업이 등록되었는지 검사(`tests/core/test_beat_schedule.py`) |
| 예약된 대기자 승격·LMS 대조가 명령 감사 기록을 남기지 않았다 | 원본 스케줄러는 Artisan 명령을 실행해 `command.executed`가 남았다. 작업이 `waitlist_promote`, `lms_reconcile` 명령을 부르도록 바꿨다(`admission.expire_drafts`와 같은 방식) | 같은 파일, `tests/lms/test_lms.py` |
| SMTP 사용자·비밀번호·암호화 설정이 없었다 | `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION`(`starttls`/`ssl`), `MAIL_TIMEOUT`. 잘못된 값은 시작 시 오류 | `manage.py check` |
| 관리 대시보드 앱 제목이 모든 언어에서 영어(Admission, Audit) | 대시보드가 Django 앱 이름을 그대로 썼다. `get_app_list`가 사이드바와 같은 번역된 메뉴 그룹 이름을 쓰고 같은 그룹 앱을 합친다 | `tests/admin/test_admin_panel.py` |
| 세션 유휴 만료(F3) | `SESSION_SAVE_EVERY_REQUEST`는 요청마다 쓰기가 생겨, 로그인한 세션의 만료를 최대 5분(`SESSION_REFRESH_SECONDS`)에 한 번만 늘리는 `SlidingSessionExpiryMiddleware`를 넣었다. 유휴 한도 115~120분, 쓰기는 사용자당 5분에 최대 한 번 | `tests/security/test_session_expiry.py` |
| `setup_demo`를 `setup_install` 전에 돌리면 `KeyError` | 필수 데이터가 없으면 "Run `manage.py setup_install` first."로 끝난다 | `tests/setup/test_setup_commands.py` |
| 배포 체크리스트 환경 변수 표 | `DB_PREPARE_THRESHOLD`(부하 테스트 결정값), `MAIL_*` 추가(4개 언어) | 문서 |

## 8. 완료 기준

계획서 Phase 13 항목

| 항목 | 결과 | 근거 |
|---|---|---|
| 부하 테스트(대용량 데모, Locust, 워커·풀 결정) | 충족(기준 미충족 기록) | 4절. 실패·초과 등록 0. p95는 공유 개발 머신에서 미충족, 스테이징 재측정 필요 |
| 보안 점검(5.1 반영 확인, 5.2 재작성) | 충족 | 5절, `security-review.md` |
| 스키마 동등성 전체 검증, 보고서 7종 CSV 비교 | 충족 | 2절, 3절 |
| Django 6.2 LTS(2027-04 이후면), Python 3.15 검토 | 해당 없음 | 6.2 LTS 미출시(2027-04 예정). Python 3.15는 Django 6.1.3(2026-11-03 예정)부터 지원하므로 그 뒤 올린다 |
| 명령·매뉴얼 최종 정리, 4개 언어 매뉴얼·README·스크린샷, 언어 추가 가이드 | 충족 | 6절 |
| 설치 리허설(외부 참여자) | 미실시 | 외부 참여자 필요. 10절 |
| 백업·복구 훈련, 배포 체크리스트 | 문서 충족, 훈련 미실시 | 백업·복구 매뉴얼에 훈련 절차. 실제 훈련은 운영 환경에서 |
| `v1.0.0` 태그 | 로컬 태그 | 이 보고서를 포함한 커밋. 원격 저장소 push는 하지 않았다(9절) |

13.5절 공통 완료 기준

| 기준 | 결과 |
|---|---|
| 테스트 | 1,090개 통과, 원본 테스트 파일 76개 모두 대응(완료 71, 부분 5, `porting/test-mapping.md`) |
| 정적 검사 | ruff, mypy strict, raw SQL, bandit, pip-audit, 명명 검사, 번역 누락 0 |
| 스키마 | 지문·모델 대조 테스트 + `pg_dump` 전체 비교 |
| 설치·데모 | 빈 DB에서 `setup_install`, `setup_demo --size=small` 성공 |
| 결과 보고 | 이 문서 |

## 9. CI

GitHub Actions(`.github/workflows/ci.yml`: 품질, 테스트 job)는 이 작업 환경에서 GitHub에 연결할 수 없어 실행하지 못했다. 같은 단계(ruff, mypy, raw SQL, 명명 검사, 번역 누락, pip-audit, PostgreSQL 18·Redis 8·Gotenberg 8 위 pytest)를 로컬에서 실행해 모두 통과했다. 처음 push할 때 CI 결과를 확인해야 한다. Phase 0 메모(`phase-0-ci-notes.md`)의 서비스 컨테이너 설정도 그때 함께 확인한다.

## 10. 남은 일

- **부하 기준 재측정:** 운영과 같은 구성의 스테이징(앱 서버와 DB 분리, 워커 코어×2+1, 풀, 준비된 문장)에서 200·500 VU로 p95를 재측정한다.
- **CI 첫 실행 확인**(9절)과 운영 Docker 이미지 빌드 확인(이 환경에서는 이미지 빌드를 끝까지 확인하지 못했다).
- **설치 리허설:** 프로젝트 밖 사람이 매뉴얼만으로 설치부터 첫 학기까지 진행한다.
- **번역 검수:** 영문·중문·라오어 매뉴얼과 라오어 UI의 원어민 검수.
- **보안 후속 과제:** `security-review.md`의 남은 항목(H2 CSV 가져오기 범위 검사, M2~M4, M9 기기 목록·전체 로그아웃 화면: allauth `usersessions`).
- **Flower 보호:** Flower는 원본 Horizon처럼 `queue_monitor.view`로 막혀 있지 않다. 내부망 또는 Nginx 인증 뒤에 두라고 문서에 적었다. 필요하면 Django 인증 프록시 뷰를 만든다.
- **저장소 분리:** 여러 DB가 같은 `storage/private`를 쓰면 미디어 id가 겹쳐 파일이 서로 덮인다(개발 환경에서 데모 DB를 여러 개 만들 때). 개발 문서에 DB마다 `PRIVATE_MEDIA_ROOT`를 따로 두라고 적을 것.
- **업그레이드:** Django 6.2 LTS(2027-04), Python 3.15(Django 6.1.3 이후).
