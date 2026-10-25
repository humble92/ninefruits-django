# 장애 대응

- 대상: IT 운영자
- 관련: [배포 체크리스트](deployment-checklist.md), [예약 작업](scheduled-jobs.md), [명령 레퍼런스](commands.md)

| 증상 | 점검 |
|---|---|
| 로그인 후 바로 보안 화면으로 이동 | 2단계 인증 정책이 "필수"이고 유예 기간이 지났다. 사용자가 등록하면 해결. 정책은 **설정 > 보안** |
| 관리 화면 403 | 사용자에게 `admin_panel.access` 권한(`관리 화면 사용`)이 있는 유효한 역할 할당이 없다. **사용자와 권한 > 사용자**에서 사용자를 열고 **역할 할당** 목록(기간, 범위) 확인 |
| 메뉴가 보이지 않음 | 해당 화면 권한(예: `roles.view`)이 역할에 없다 |
| 이메일 코드가 오지 않음 | 메일 설정(`MAIL_*`, `DEFAULT_FROM_EMAIL`), **감사 > 보안 이벤트**의 `이메일 코드 발송` 기록, 발송 제한(사용자당 1분 1회, 1시간 5회) |
| 로그인 화면이 `429 Too Many Requests` | 한 주소에서 1분에 `LOGIN_RATE_LIMIT_PER_IP`(기본 30)회를 넘었다. 여러 사용자가 한꺼번에 막히면 `TRUSTED_PROXY_COUNT`가 실제 프록시 수와 맞는지(모두 Nginx 주소로 보이는지), 캠퍼스 NAT라면 값을 늘린다([배포 체크리스트](deployment-checklist.md#프록시와-클라이언트-주소)) |
| 비밀번호가 맞는데 로그인 실패 | 로그인 잠금(**보안 이벤트**의 `로그인 잠금`) 또는 비활성 계정. 잠금 해제: `uv run manage.py security_unlock_user <이메일> --reason="..."` |
| 화면에 다른 사람 데이터가 0건 | 정상일 수 있다(행 단위 보안). DB 세션 수행자가 설정되었는지 **감사 > 데이터 변경 기록**의 사용자 열로 확인 |
| `400 Bad Request` | 요청한 호스트 이름이 `DJANGO_ALLOWED_HOSTS`에 없다 |
| `403 CSRF verification failed` | `DJANGO_CSRF_TRUSTED_ORIGINS`에 `https://` 주소가 없거나 Nginx가 `X-Forwarded-Proto`를 넘기지 않는다 |
| HTTPS 리디렉션이 끝없이 반복 | Nginx가 `X-Forwarded-Proto $scheme`을 넘기지 않아 Django가 HTTP 요청으로 본다(`SECURE_PROXY_SSL_HEADER`) |
| 화면 스타일·스크립트가 없음, `manifest.json` 오류 | `npm ci && npm run build`(`static/dist/`), `collectstatic`, Nginx `/static/` 경로. 운영에서는 `VITE_DEV_MODE=false` |
| 화면 일부가 영어로 나옴 | `compilemessages --ignore=.venv`를 실행하지 않았다(`.mo` 없음). 새 문자열이면 `uv run manage.py i18n_missing <locale>` |
| `permission denied for schema public` | 애플리케이션이 `app_runtime`으로 DDL을 시도했다. 마이그레이션은 `uv run manage.py migrate` 또는 `setup_install`(자동으로 `app_migrator` 사용)로만 실행 |
| `Audit records are append-only` | 감사 테이블 수정/삭제 시도. 정상적인 차단이다 |
| PDF 생성 실패 | `uv run manage.py pdf_sample`, Gotenberg 상태, `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` |
| 큐 작업이 멈춤 | Flower에서 worker 연결과 실패 작업 확인, `uv run celery -A config inspect active`, Redis 연결(`REDIS_URL`) |
| 예약 작업이 돌지 않음, `/api/v1/health/`가 `degraded` | beat가 멈췄다(스케줄러 심장박동이 5분 넘게 없음). beat 프로세스와 로그 확인. beat는 한 대만 |
| worker 로그에 `Received unregistered task` | worker가 이전 코드로 돌고 있다. 배포 뒤 worker를 다시 시작한다 |
| 학기 마감이 끝나지 않음 | Flower의 `grading.close_term_records` 실패 작업. 원인을 고친 뒤 학기 마감을 다시 시작한다(학생별 계산은 다시 실행해도 같은 결과) |

요청 단위 추적: 응답 헤더 `X-Request-Id` 값으로 로그(JSON의 `request_id`), 업무 감사, 데이터 변경 기록, 보안 이벤트를 함께 검색할 수 있다. Nginx가 `X-Request-Id $request_id`를 넘기면 Nginx 접근 로그와도 이어진다. 명령 실행은 `cmd-`로 시작하는 실행 ID를 쓴다.
