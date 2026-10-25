# 감사 무결성과 정기 정리

- 대상: IT 운영자, 보안 담당
- 관련: [관리자 매뉴얼 4장 감사 조회](../admin/04-audit.md), [명령 레퍼런스](commands.md), [백업과 복구](backup-restore.md)

## 감사 해시 체인

감사 테이블(`audit.record_changes` 데이터 변경 기록, `audit.activity_log` 업무 감사, `audit.security_events` 보안 이벤트)은 추가만 가능하다(트리거). 여기에 더해 변조를 **드러내는** 장치가 있다.

- 행마다 삽입 시 내용의 SHA-256(`row_hash`)이 붙는다.
- `audit_seal`(예약 작업 `audit.seal`, 매일 03:30)이 새 행을 ID 순서로 체인에 잇는다: `chain_hash = SHA-256(이전 chain_hash || row_hash)`. 스키마 소유자 연결(`migrator`)로 DB 함수 `audit.seal()`을 호출한다.
- `audit_verify_chain`이 모든 행의 내용 해시와 체인을 다시 계산한다. 테이블마다 검사 수, 봉인 수, 불일치 수와 첫 불일치 id를 출력하고, 내용이 바뀐 행은 "row mismatch", 빠지거나 순서가 바뀐 행은 "chain mismatch"로 나오며 종료 코드 2를 돌려준다.

```bash
uv run manage.py audit_seal
uv run manage.py audit_verify_chain
uv run manage.py audit_verify_chain --table=security_events
```

유의점

- 봉인 전(그날 안)에 바뀐 행은 체인으로 잡지 못한다. 그래서 봉인은 매일, 검증은 백업 전과 보안 점검 때 한다.
- 정리(`audit_prune`)로 앞부분을 지우면 남은 첫 행의 연결은 검사하지 않는다(지운 범위는 정리 명령의 감사 기록에 남는다).
- DB 관리자(스키마 소유자 `app_migrator`)만 `app.audit_maintenance = on`으로 바꿀 수 있다. 애플리케이션 역할(`app_runtime`)은 감사 테이블에 UPDATE·DELETE 권한이 없다.

## 보존과 정리

1. 보존 기간을 정한다(예: 데이터 변경 기록 3년, 업무 감사 5년, 보안 이벤트 1년).
2. 정리 전 백업([백업과 복구](backup-restore.md))을 받고 `audit_verify_chain`으로 체인이 온전한지 확인한다.
3. `uv run manage.py audit_prune --before=YYYY-MM-DD --table=record_changes --dry-run`으로 건수를 보고, `--dry-run` 없이 실행한다(`--actor=`로 실행자 계정을 남긴다). 봉인되지 않은 행은 지우지 않으므로 먼저 `audit_seal`을 돌린다.
4. 정리 뒤 `audit_verify_chain`을 다시 돌린다.

정리 자체의 기록: 실행마다 업무 감사(로그 `command`)에 기준일·옵션·실행자·OS 사용자와 테이블별 **삭제 행 수, 삭제 ID 범위, 경계의 chain_hash**가 남고, 실제 삭제는 보안 이벤트 `audit.pruned`로도 남는다(**감사 > 보안 이벤트**). 이 기록 행도 다음 봉인에서 체인에 들어간다. `audit_verify_chain`이 남은 첫 행의 연결을 검사하지 않는 이유가 바로 이 경계이며, 경계 해시와 정리 기록을 맞춰 보면 지워진 범위가 기록된 정리와 일치하는지 확인할 수 있다.

## 파일 정리

`uv run manage.py media_prune_orphans --dry-run`은 소유자가 사라진 미디어 행과 행이 없는 디렉터리(`PRIVATE_MEDIA_ROOT/<media id>/`)를 보여 주고, `--dry-run` 없이 지운다. 인물 사진, 지원 서류, 증명서 PDF, 시험 증빙이 대상이다. 월 1회 또는 대량 삭제 뒤에 실행한다.

## 상태 점검

| 점검 | 방법 | 실패 시 |
|---|---|---|
| 서비스 상태 | `GET /api/v1/health/`(로그인 불필요, 로드 밸런서·모니터링용) | DB나 캐시가 응답하지 않으면 `unavailable`(503), 스케줄러 심장박동이 5분 넘게 없으면 `degraded`(200), 정상이면 `ok`. `관리 화면 사용` 권한으로 로그인해 열면 항목별 결과(`database`, `cache`, `scheduler`)도 보인다 |
| 전체 점검 | `uv run manage.py system_health_check [--json]` | 키, DB 역할, RLS, 마이그레이션, 권한 카탈로그, Redis, Celery 워커, Gotenberg, 저장소, beat 심장박동 12개 항목. 하나라도 실패하면 종료 코드 2 |
| 운영 설정 | `uv run manage.py check --deploy` | `DEBUG`, HTTPS 리디렉션, HSTS, 보안 쿠키, 비밀 키 경고 |
| 마이그레이션 | `uv run manage.py migrate --check` | 적용하지 않은 마이그레이션이 있으면 종료 코드 1 |
| 권한 카탈로그 | `uv run manage.py security_sync_permissions` | 코드의 권한 목록을 DB에 반영한다(다시 실행해도 안전) |
| PDF 서비스 | `uv run manage.py pdf_sample` | Gotenberg 연결, 글꼴 |
| 번역 | `uv run manage.py i18n_missing --strict` | 누락이 있으면 종료 코드 2 |
| 감사 체인 | `uv run manage.py audit_verify_chain` | 불일치가 있으면 종료 코드 2 |
| 큐 | Flower, `uv run celery -A config inspect ping` | worker가 응답하지 않는다 |

모니터링에는 `/api/v1/health/`의 HTTP 상태와 `status` 값을 연결하고, 나머지는 배포 때와 [정기 점검](deployment-checklist.md#정기-점검)에서 실행한다.
