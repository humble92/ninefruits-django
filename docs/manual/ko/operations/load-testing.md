# 부하 테스트 (수강신청 피크)

- 대상: IT 운영자
- 관련: [배포 체크리스트](deployment-checklist.md), [설치](installation.md), [명령 목록](commands.md)

수강신청 첫날 아침처럼 많은 학생이 같은 강좌에 동시에 몰리는 상황을 Locust로 재현한다. 스크립트는 `loadtest/registration.py`(원본 k6 `tests/load/registration.js`), 실행 도우미는 `loadtest/run.sh`, 초과 등록 점검은 `loadtest/seat_check.sql`.

[매뉴얼 목차](../README.md)

## 준비

1. 부하 테스트 전용 데이터베이스를 만든다(운영 DB에서 하지 않는다). 역할과 DB 생성은 [설치](installation.md) 2절과 같고, 이후 설치와 대용량 데모를 넣는다. 학생 계정 목록 CSV가 비공개 저장소(`PRIVATE_MEDIA_ROOT`, 기본 `storage/private`)의 `load-accounts.csv`에 생긴다.

   ```bash
   export DB_DATABASE=nf_load
   uv run manage.py setup_install --profile=korean-university --grade-scale=4.5 --force < /dev/null
   uv run manage.py setup_demo --size=large --seed=42 --student-accounts --force
   ```

2. 수강신청 기간이 열려 있어야 한다. 데모는 다음 학기 수강신청 기간을 학년별로 만든다(4학년은 이미 열림, 3학년은 2일 뒤, 1·2학년은 3일 뒤). 전 학년을 대상으로 측정하려면 관리자 화면 학기 **수정** 화면의 **업무 기간**([관리자 매뉴얼 10장](../admin/10-terms.md))에서 나머지 수강신청 기간의 시작 시각을 지금 이전으로 바꾸거나, 테스트 DB에서 superuser로 다음을 실행한다.

   ```sql
   UPDATE term_windows SET opens_at = now() - interval '1 hour'
    WHERE window_type = 'registration' AND opens_at > now() AND closes_at > now();
   ```

3. Redis와 Celery 워커가 떠 있어야 한다. 좌석은 DB에서 바로 정해지지만 대기자 승격, LMS 동기화, 알림은 큐가 처리한다. 다른 작업과 Redis를 같이 쓰면 `REDIS_URL=redis://127.0.0.1:6379/7`처럼 다른 DB 번호를 쓴다.

## 실행

`loadtest/run.sh`가 gunicorn(`config/gunicorn.py`)과 Celery 워커를 띄우고 Locust를 headless로 돌린 뒤 좌석 점검까지 하고 모두 내린다.

```bash
export DB_DATABASE=nf_load DB_POOL=true DB_POOL_MIN=1 DB_POOL_MAX=2 DB_PREPARE_THRESHOLD=2
WORKERS=9 USERS=100 DURATION=1m loadtest/run.sh storage/loadtest/w9-u100
```

직접 돌릴 때는 서버를 `TRUSTED_PROXY_COUNT=1`로 띄우고 Locust를 실행한다.

```bash
TRUSTED_PROXY_COUNT=1 DJANGO_DEBUG=false GUNICORN_WORKERS=9 uv run gunicorn config.wsgi -c config/gunicorn.py
uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \
    --host http://127.0.0.1:8000 --csv storage/loadtest/run
psql -h 127.0.0.1 -U postgres -d nf_load -v term=<학기 id> -f loadtest/seat_check.sql
```

- 시나리오: 로그인(`/accounts/login/`) → 수강신청 화면 → 강좌 검색(HTMX `?partial=results`) → 빈자리가 있는 첫 분반 등록 → 취소. 반복마다 쿠키를 지우고 다음 학생으로 로그인한다. 만석·규칙 거절은 정상 결과로 센다(`registration outcomes`).
- 등록·취소 버튼은 HTMX처럼 `HX-Request`로 POST하고, 서버는 302로 수강신청 화면을 돌려준다. `enroll`·`drop` 시간에는 그 화면까지 포함된다(브라우저도 그 화면을 받아야 `#registration`을 바꾼다).
- 학생마다 다른 `X-Forwarded-For` 주소를 보낸다. 서버를 프록시 1단 뒤(`TRUSTED_PROXY_COUNT=1`)로 띄우면 allauth의 주소당 로그인 제한이 실제 캠퍼스처럼 학생 주소마다 적용된다. `ADDRESSES=1`이면 모든 학생이 한 주소(NAT) 뒤에 있는 상황을 재현한다.
- 환경 변수: `ACCOUNTS`(계정 CSV), `SEARCH`(검색어, 기본 `GEN`), `ADDRESSES`, `FIRST_ACCOUNT`(시작 계정, 기본 무작위). `run.sh`는 `WORKERS`, `USERS`, `SPAWN_RATE`, `DURATION`, `TERM_ID`, `PORT`를 받는다.
- `USERS`를 100 → 200 → 500으로 올리며 페이지별 p95와 실패율을 본다. 기준: 수강신청 화면 p95 < 800ms, 등록 p95 < 1.5s, 실패율 < 1%. 기준을 넘으면 Locust가 종료 코드 1로 끝난다.
- 서버 쪽에서는 `pg_stat_activity`의 연결 수와 잠금 대기(`wait_event_type = 'Lock'`), Celery 처리 지연, CPU 포화를 함께 본다. Locust를 같은 서버에서 돌리면 Locust도 CPU를 쓰므로 수치는 하한선이다.

## 설계상 보장되는 것

- 정원은 분반 행 잠금(`SeatAllocator.lock`, `SELECT ... FOR NO KEY UPDATE`)과 CHECK 제약으로 지켜진다. 동시 요청이 몰려도 초과 등록은 나지 않는다(`tests/registration/test_concurrent_registration.py`: 16개 프로세스, 5석). 잠금은 같은 분반의 좌석을 잡는 요청끼리만 기다리게 하고, 분반을 참조하기만 하는 행(등록 시도 기록, LMS 동기화 기록)의 외래 키 확인은 막지 않는다.
- 측정 후 `loadtest/seat_check.sql`의 네 쿼리가 모두 0행이어야 한다(정원 초과, 좌석 카운터 불일치, 좌석 그룹 초과, 같은 분반 중복 등록).
- 수강신청 화면의 쿼리 수는 등록·대기·검색 결과 수와 무관하다(`tests/registration/test_portal_query_count.py`).

## 로그인 주소 제한과 프록시

allauth는 계정별 실패 제한(분당 5회) 외에 **주소당 로그인 제한**(`LOGIN_RATE_LIMIT_PER_IP`, 기본 `30/m/ip`)을 둔다. 원본에는 없던 제한이다. 앱이 보는 주소는 `TRUSTED_PROXY_COUNT`로 정한다(`ninefruits.core.http.client_ip`).

- Nginx 뒤에서 `TRUSTED_PROXY_COUNT=0`(기본)으로 두면 모든 요청의 주소가 Nginx 주소 하나가 된다. 캠퍼스 전체가 NAT 주소 하나로 나가는 경우도 같다.
- 이 상태를 재현한 측정(`ADDRESSES=1`, 100 VU, 1분)에서 로그인 4,876회 중 **30회만 성공**하고 4,846회가 429로 거절됐다(실패율 49%). 1분 동안 등록은 20건에 그쳤다. 주소를 학생마다 나눈 같은 조건에서는 로그인 거절 0건이다.
- 운영 설정: 프록시 단수만큼 `TRUSTED_PROXY_COUNT`를 둔다(Nginx 1단이면 `1`). 학생 대부분이 NAT 주소 하나 뒤에 있으면 피크 로그인 수에 맞춰 `LOGIN_RATE_LIMIT_PER_IP`를 올린다. 예: 재학생 2,000명이 10분 안에 로그인하면 주소 하나에서 분당 200회이므로 `300/m/ip`. 빈 값이면 주소당 제한이 없어진다(원본과 같음, 계정별 실패 제한은 남는다).

## 서버 구성 결정

- **gunicorn sync 워커**(`config/gunicorn.py`). 워커 수 `GUNICORN_WORKERS`의 기본은 CPU 코어 × 2 + 1. 측정에서 처리량은 CPU에 묶였고, 4코어에서 워커 4·9·16개의 처리량은 같았다(초당 23~26건). 워커를 더 늘리면 DB 연결(12 → 36)과 잠금 대기(최대 1 → 12)만 늘었다. 코어 × 2 + 1보다 늘리지 말고 앱 서버를 수평 확장한다.
- **연결 풀과 준비된 문장**: `DB_POOL=true`, `DB_POOL_MIN=1`, `DB_POOL_MAX=2`, `DB_PREPARE_THRESHOLD=2`. 행 수준 보안(RLS) 정책 때문에 쿼리 계획 수립이 페이지 DB 시간의 대부분이었다(수강신청 화면 쿼리 31개: 계획 51ms, 실행 19ms). 연결을 재사용하고 서버 측 바인딩으로 준비된 문장을 쓰면 연결마다 한 번만 계획한다. 같은 4코어에서 처리량이 초당 16.8건에서 25.6건으로, 1명일 때 수강신청 화면 중앙값이 160ms에서 97ms로 줄었다. 필요한 연결 수는 서버당 워커 수 × `DB_POOL_MAX` + Celery 동시성이고 PostgreSQL `max_connections`보다 작아야 한다. PgBouncer를 transaction 모드로 앞에 두면 준비된 문장을 쓸 수 없으니 `DB_PREPARE_THRESHOLD=0`으로 둔다. 전체 테스트(1,066개)는 이 설정에서도 통과한다.
- **ASGI(원본의 Octane 판단에 해당)**: 도입하지 않는다. 화면이 모두 동기 뷰라 ASGI에서는 스레드로 넘겨 실행되어 이득이 없고, 처리량은 CPU 코어 수에 비례한다. Django는 요청마다 앱을 다시 부트스트랩하지 않으므로(PHP-FPM과 다름) Octane이 주던 이득은 이미 있고, 연결 재사용의 이득은 위의 풀·준비된 문장으로 얻는다.
- 로그인은 Argon2 해시 확인 때문에 요청당 CPU가 크다(1명일 때 약 140ms). 피크 로그인이 몰리면 이 비용이 처리량을 먼저 깎는다.

## 2026-10-24 측정 결과

환경: 4 vCPU(Xeon 2.1GHz, `nproc` = 4), RAM 15GB, 다른 작업(테스트 실행)과 공유하는 개발 머신(측정 중 load average 7~21), Locust·gunicorn·PostgreSQL 18·Redis가 같은 머신. Python 3.14, Django 6.1, gunicorn 26.2, `DJANGO_DEBUG=false`. 데모 `--size=large --seed=42`(학생 20,004명, 학생 계정 11,437개, 생성 416초), 2027년 봄학기 수강신청 기간을 전 학년에 개방, 공개 분반 52개(총 정원 2,262). 1분씩, `TRUSTED_PROXY_COUNT=1`, 학생마다 다른 주소.

| 조건 | 처리량 | 화면 p95 | 등록 p95 | 실패 | 등록 성공/거절 | PG 연결 최대 |
|---|---|---|---|---|---|---|
| 2 VU, 워커 9, 풀 없음 | 5.1 req/s | 200ms | 640ms | 0 / 300 | 50 / 0 | 3 |
| 2 VU, 워커 9, 풀 + 준비된 문장 | 6.2 req/s | 160ms | 470ms | 0 / 372 | 62 / 0 | 22 |
| 100 VU, 워커 4, 풀 없음 | 16.8 req/s | 6.0s | 11s | 0 / 1,005 | 52 / 86 | 6 |
| 100 VU, 워커 16, 풀 없음 | 17.1 req/s | 6.1s | 11s | 0 / 1,027 | 60 / 86 | 18 |
| 100 VU, 워커 4, 풀 + 준비된 문장 | 25.6 req/s | 4.1s | 7.0s | 0 / 1,536 | 97 / 155 | 12 |
| 100 VU, 워커 9, 풀 + 준비된 문장 | 25.4 req/s | 4.5s | 7.3s | 0 / 1,523 | 77 / 167 | 22 |
| 100 VU, 워커 16, 풀 + 준비된 문장 | 23.4 req/s | 4.6s | 8.4s | 0 / 1,405 | 131 / 79 | 36 |
| 200 VU, 워커 9, 풀 + 준비된 문장 | 29.8 req/s | 9.4s | 14s | 0 / 1,792 | 66 / 172 | 22 |
| 200 VU, 워커 16, 풀 + 준비된 문장 | 29.2 req/s | 9.1s | 14s | 0 / 1,761 | 53 / 174 | 36 |
| 100 VU, 워커 9, 한 주소(NAT) | (429 응답 위주) | 2.0s | 3.3s | 4,846 / 9,862 | 20 / 10 | 22 |

읽는 법

- 모든 측정에서 HTTP 실패 0(한 주소 측정 제외), 초과 등록 0(`seat_check.sql` 0행). 등록 거절은 만석(`capacity`)과 같은 교과목 중복(`duplicate_course`, 앞선 측정이 끝날 때 끊긴 반복이 남긴 등록)으로 정상 동작이다.
- 100 VU에서의 수 초 지연은 요청 대기열이다. 요청 하나의 서버 처리 시간은 1명일 때 화면 약 100ms, 등록(POST + 돌아온 화면) 약 290ms이고, 4코어를 Locust·PostgreSQL·다른 작업과 나눠 쓰는 이 머신의 상한이 초당 25~30건이다. 기준(화면 p95 < 800ms, 등록 p95 < 1.5s)은 이 머신에서 100 VU로는 맞추지 못한다.
- 잠금 대기는 같은 분반 좌석 잠금에서만 생겼고 짧았다(측정 중 순간 최대 1~12건, 워커가 많을수록 많음). DB 연결은 워커 × 2 이하.
- 수강신청 피크를 "10분 동안 재학생 2,000명이 각 6회 요청"으로 잡으면 초당 20건이다. 이 머신(풀 + 준비된 문장)에서 초당 25~30건이 나왔으므로 전용 8코어 앱 서버라면 여유가 있다. 운영 전 할 일: 운영과 같은 구성(전용 앱 서버, Nginx, 별도 DB 서버, Locust는 다른 머신)의 스테이징에서 같은 스크립트를 200·500 VU로 다시 돌려 기준을 확인한다.
- 원본(Laravel, 개발용 Sail, 내장 서버)은 100 VU에서 워커 4개 24.7 req/s, 16개 34.5 req/s였다. 머신이 달라 직접 비교는 어렵다.
