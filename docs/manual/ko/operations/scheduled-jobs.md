# 예약 작업과 큐

- 대상: IT 운영자
- 관련: [배포 체크리스트](deployment-checklist.md), [감사 무결성](audit-and-maintenance.md), [명령 레퍼런스](commands.md)

## 상시 프로세스

| 프로세스 | 명령 | 확인 |
|---|---|---|
| 웹 | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| 큐 워커 | `uv run celery -A config worker --loglevel=INFO` | Flower의 **Workers**, `uv run celery -A config inspect ping` |
| 스케줄러 | `uv run celery -A config beat --loglevel=INFO` (**전체에서 한 프로세스만**) | `/api/v1/health/`의 `scheduler`, beat 로그 |
| 큐 모니터(선택) | `uv run celery -A config flower --port=5555` | 내부망이나 Nginx 접근 제한 뒤에만 둔다 |

세 프로세스 모두 같은 코드와 환경 변수를 쓴다. systemd 예:

```ini
# /etc/systemd/system/ninefruits-celery.service
[Service]
User=ninefruits
WorkingDirectory=/srv/ninefruits
EnvironmentFile=/etc/ninefruits/env
ExecStart=/usr/local/bin/uv run --no-sync celery -A config worker --loglevel=INFO
KillSignal=SIGTERM
TimeoutStopSec=300
Restart=always
```

beat는 `ExecStart=... celery -A config beat --loglevel=INFO`로 같은 형식의 서비스를 하나 더 만든다. 서버가 여러 대여도 beat 서비스는 한 대에서만 켠다.

## 예약 작업

등록 내용은 `config/celery.py`의 `beat_schedule`이고 beat가 시작할 때 django-celery-beat DB 스케줄러(`django_celery_beat_*` 테이블)에 맞춘다. 시각은 서버 시간대(`APP_TIMEZONE`, 기본 UTC) 기준이다. 모든 예약 작업은 Redis 잠금(`single_instance`)으로 같은 작업이 동시에 두 번 돌지 않는다.

| 작업 (Celery 이름) | 주기 | 같은 일을 하는 명령 | 실패 감지 |
|---|---|---|---|
| `admission.expire_drafts` | 매일 03:10 | `admission_expire_drafts` | 명령을 그대로 실행하므로 업무 감사(로그 `command`)에 실행마다 기록된다. 기록이 하루 넘게 없으면 beat와 worker를 확인한다 |
| `registration.release_reserved_seats` | 5분마다 | `registration_release_reserved_seats` | 감사 기록 없음. 전환 시각이 지난 좌석 할당의 `release_processed_at`이 비어 있으면 beat를 확인한다 |
| `registration.promote_waitlists` | 매시 정각 | `waitlist_promote` | 업무 감사 기록 없음(승격된 수강은 데이터 변경 기록에 `system:task:registration.promote_waitlists`로 남는다). Flower의 작업 결과(강좌 수, 승격 수) |
| `lms.reconcile` | 매일 02:30 | `lms_reconcile` | 연결별 동기화 기록(관리 화면 **LMS 연동**), Flower의 작업 결과 |
| `audit.seal` | 매일 03:30 | `audit_seal` | 감사 해시 체인 봉인([감사 무결성](audit-and-maintenance.md)). `audit_verify_chain`의 봉인되지 않은 행 수가 하루치보다 많으면 확인한다 |
| `core.heartbeat` | 매분 | 없음 | 캐시 키 `system:heartbeat`에 마지막 실행 시각을 적는다. `/api/v1/health/`가 5분 넘게 갱신이 없으면 `degraded`로 답한다 |

## 큐 작업

| 작업 (Celery 이름) | 발생 | 비고 |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | 레코드 묶음별 작업(group). 실패한 묶음이 있으면 명령을 다시 실행한다(이미 현재 키인 레코드는 건너뛴다) |
| `registration.promote_waitlist` | 수강 취소·철회, 좌석 할당 전환 | 강좌별 Redis 잠금으로 하나만 실행된다(중복 방지). 대기자 승격은 모든 수강 규칙을 다시 확인한다. 트랜잭션 커밋 뒤에 큐에 들어간다 |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, 관리 화면 학기 마감 | chord: 학생 100명 단위 작업 뒤 마무리 작업(성적우수 순위, 학기 상태 변경, 시작한 직원에게 알림). 진행률은 `job_batches`의 `term-close:{학기 코드}` 행으로 관리 화면에 보인다. 묶음 작업은 DB 오류 시 3번까지 다시 시도하고, 그래도 실패하면 묶음 전체가 실패로 표시되어 마무리 작업이 실행되지 않는다. 원인을 고친 뒤 학기 마감을 다시 시작한다(학생별 계산은 다시 실행해도 같은 결과) |
| `importing.import_chunk` | 관리 화면 CSV 가져오기, `reference_import` | 묶음별 작업. 결과는 `imports`, 실패 행은 `failed_import_rows`(관리 화면 가져오기 결과) |
| `lms.sync_section`, `lms.sync_enrollment` | 개설강좌·수강 변경 이벤트 | 실패하면 1분 뒤 3번까지 다시 시도한다. 남은 차이는 야간 `lms.reconcile`이 맞춘다 |

큐 작업은 실행 중 DB 수행자가 `system:task:{작업 이름}`(예: `system:task:grading.close_term_records`)으로 기록되고, 작업을 일으킨 요청의 요청 ID와 사용자가 함께 남는다.

Flower에서 실패 작업(**Tasks**, 상태 `FAILURE`)과 예외를 본다. Celery 작업은 `acks_late`이므로 worker가 작업 중에 죽으면 다시 실행된다. 모든 작업은 다시 실행해도 같은 결과가 나오도록(멱등) 만들어져 있다.
