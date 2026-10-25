# LMS 연동 가이드

- 작성일: 2026-10-24 (Phase 12, 원본 [LMS 연동 가이드](https://github.com/humble92/ninefruits-laravel/blob/main/docs/lms-integration-guide.md)를 Django·Python 커넥터 기준으로 다시 씀)
- 대상: LMS 연동을 구현할 개발자, 연동을 운영할 시스템 관리자
- 관련: [이식 계획 12절](../porting/porting-plan.md#12-lms-연동과-api), 원본 [ADR 0017](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0017-lms-integration.md), [ADR 0004-django (API 토큰)](../porting/decisions/0004-django-api-tokens.md), [관리자 매뉴얼 28장](manual/ko/admin/28-lms-integration.md), [운영 명령](manual/ko/operations/commands.md#lms-연동-phase-12)

## 1. 원칙

| 데이터 | 원본 | 흐름 |
|---|---|---|
| 사용자, 개설강좌, 수강 명단 | 학사 시스템 | 학사 → LMS (이벤트 즉시 + 야간 대조) |
| 강의 콘텐츠, 과제, 퀴즈, 원점수 | LMS | LMS 안에 머묾 |
| 최종 점수 | LMS → 학사 **초안** | 교원이 성적 입력 화면에서 불러와 확인 후 저장·제출 |
| 확정 성적 | 학사 시스템 | LMS로 보내지 않음 |

학사 시스템은 특정 LMS에 묶이지 않는다. 플랫폼마다 **드라이버**(어떤 커넥터로 말하는가)와 인증 정보를 두고, 같은 커넥터로 여러 플랫폼(캠퍼스별 Moodle 등)을 운영할 수 있다.

## 2. 만들어진 기반

| 구성 | 위치 |
|---|---|
| 표 `lms_platforms`(드라이버, URL, 암호화된 인증 정보, 옵션), `lms_course_links`(개설강좌 ↔ 플랫폼 강좌), `lms_user_links`(사용자 ↔ 플랫폼 사용자), `lms_sync_logs`(단계별 결과) | 모델 `ninefruits/lms/models.py`. 표·제약·감사 트리거·RLS 정책(`db/sql/policies/lms.sql`)은 원본 DDL 재생(`core/0047`) |
| 커넥터 인터페이스 `LmsConnector`(`typing.Protocol`): `ensure_course`, `ensure_user`, `enroll`, `unenroll`, `members`, `final_scores` | `ninefruits/lms/connectors/base.py` |
| `NullConnector`: 호출 없이 결정적 ID(`course-{개설강좌 id}`, `user-{사용자 id}`)를 돌려준다. 플랫폼 구성원은 항상 비어 있다고 답해 대조가 모두를 다시 추가한다 | `ninefruits/lms/connectors/null.py` |
| `ConnectorRegistry`: 드라이버 → 커넥터. 구현이 없는 드라이버(`moodle`, `openedx`)는 동기화 때 실패로 기록되고 강좌 연결이 "실패"가 된다 | `ninefruits/lms/connectors/registry.py`, `connectors()` |
| 이벤트 → Celery 작업(커밋 뒤): `SectionPublished` → `lms.sync_section`, `EnrollmentConfirmed`/`EnrollmentDropped` → `lms.sync_enrollment`, `GradesFinalized` → (보내지 않음). 활성 플랫폼만, 수강 명단은 **수강 명단 동기화**가 켜진 플랫폼만 | `ninefruits/lms/listeners.py`, `tasks.py` |
| Action: `SyncSection`(강좌 + 교원 + 수강생), `SyncEnrollment`, `PullGrades`, `ReconcilePlatform`, `SavePlatform`, `RecordPlatformCallback` | `ninefruits/lms/actions/` |
| 단계 기록 `SyncLogger`: 대기 → 성공/실패/건너뜀. 단계는 savepoint 안에서 돌고, 실패하면 단계의 쓰기만 되돌린 뒤 기록을 "실패"로 남기고 예외를 다시 던진다(작업이 재시도) | `ninefruits/lms/services/sync_logger.py` |
| 명령 `lms_sync {platform}`, `lms_reconcile [platform]`, beat 작업 `lms.reconcile`(매일 02:30) | `ninefruits/lms/management/commands/`, `config/celery.py` |
| 관리 화면 **LMS 연동 > LMS 플랫폼 / 강좌 연결 / 동기화 기록**, 포털 강좌 상세와 담당 강좌의 LMS 링크, 성적 입력의 **LMS 점수 불러오기** | `ninefruits/lms/admin/`, `services/portal.py`, `services/grades.py` |
| API `/api/v1/lms/platforms/...`(플랫폼 조회, 강좌 연결 목록, 동기화 결과 콜백, 점수 전달) | `ninefruits/api/views/lms.py`, 4절 |

## 3. 커넥터 구현 절차

### 3.1 클래스

`LmsConnector` Protocol의 여섯 메서드를 가진 클래스를 만든다. 상속은 필요 없다(구조적 타입). 커넥터는 **상태를 갖지 않는다**: 메서드마다 플랫폼(`platform.base_url`, `platform.credential("token")`, `platform.options`)을 받는다. HTTP는 프로젝트가 이미 쓰는 httpx로 한다.

```python
# myuniversity/lms/moodle.py
from __future__ import annotations

import httpx

from ninefruits.lms.connectors import PlatformCourse


class MoodleConnector:
    """Moodle 4.x Web Services (REST)."""

    timeout = 30

    def _call(self, platform, function: str, **params) -> object:
        response = httpx.post(
            f"{platform.base_url.rstrip('/')}/webservice/rest/server.php",
            data={
                "wstoken": platform.credential("token"),
                "wsfunction": function,
                "moodlewsrestformat": "json",
                **params,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()
        if isinstance(body, dict) and body.get("exception"):
            raise RuntimeError(f"Moodle {function}: {body.get('message')}")
        return body

    def ensure_course(self, platform, section) -> PlatformCourse:
        ...  # core_course_get_courses_by_field(idnumber=section.pk) 또는 core_course_create_courses
        return {"id": str(course_id), "url": f"{platform.base_url}/course/view.php?id={course_id}"}

    def ensure_user(self, platform, user) -> str: ...
    def enroll(self, platform, course_id: str, user_id: str, role: str) -> None: ...
    def unenroll(self, platform, course_id: str, user_id: str) -> None: ...
    def members(self, platform, course_id: str) -> dict[str, str]: ...
    def final_scores(self, platform, course_id: str) -> dict[str, float]: ...
```

- 역할 인수 `role`은 `"instructor"` 또는 `"student"`(`ninefruits.lms.enums.INSTRUCTOR`, `STUDENT`)다. 플랫폼 역할 ID는 `platform.options`(예: `{"roles": {"instructor": 3, "student": 5}}`)에 둔다. 관리 화면에는 옵션 입력이 없으므로 셸이나 데이터 마이그레이션으로 넣는다.
- 오류는 **예외로 던진다**. `SyncLogger`가 메시지(1,000자)를 실패로 기록하고 Celery 작업이 3회(60초 간격) 재시도한다. 권한 없음처럼 재시도해도 소용없는 오류는 원인이 드러나는 메시지로 던진다.
- 인증 정보는 키 이름을 정해 문서화한다(Moodle: `token`, Open edX: `client_id`, `client_secret`). 값은 `lms_platforms.credentials`에 암호화되어 저장된다(아래 3.3).

### 3.2 식별자와 멱등성

- 학사 측 키는 `sections.id`, `users.id`다. 플랫폼 측 ID는 `lms_course_links.external_course_id`, `lms_user_links.external_user_id`에 저장된다.
- 커넥터는 **같은 입력에 같은 ID**를 돌려주어야 한다. `ensure_course`·`ensure_user`는 먼저 찾고 없을 때만 만든다. 사용자 매칭 키는 기관 이메일(`student_records.institutional_email` 또는 `users.email`)을 권장한다.
- `enroll`을 두 번 불러도 결과가 같아야 한다(이미 등록된 구성원은 그대로).
- `members`는 플랫폼 강좌의 구성원 `{외부 사용자 ID: 역할}`, `final_scores`는 `{외부 사용자 ID: 점수(0~100)}`다.

### 3.3 등록과 설정

드라이버 이름(`lms_platforms.driver`, 32자)과 커넥터를 잇는 방법은 둘이다.

1. 설정 `LMS_CONNECTORS`(배포별, 코드 변경 없음):

   ```python
   # config/settings/production.py 등
   LMS_CONNECTORS = {"moodle": "myuniversity.lms.moodle.MoodleConnector"}
   ```

2. 앱의 `AppConfig.ready()`에서 등록:

   ```python
   from ninefruits.lms.connectors import connectors

   connectors().register("moodle", MoodleConnector)  # 클래스, 팩토리 함수 또는 점 경로
   ```

드라이버 목록(`LmsDriver`: `null`, `moodle`, `openedx`)에 없는 드라이버라면 `ninefruits/lms/enums.py`에 값을 추가한다(관리 화면의 선택지). 커넥터가 없는 드라이버는 관리 화면에서 "(아직 구현되지 않음)"으로 표시된다.

인증 정보는 PII 암호화 키(`PII_ENCRYPTION_KEY`, AES-256-GCM)로 암호화된다. 키를 바꾸면 이전 키(`PII_PREVIOUS_KEYS`)로 계속 읽힌다. `pii_reencrypt`는 인증 정보를 다시 암호화하지 않으므로, 이전 키를 지우기 전에 플랫폼 수정 화면에서 인증 정보를 다시 입력한다.

### 3.4 테스트 더블

실제 플랫폼 없이 커넥터 자리에 가짜를 넣어 검증한다(원본 `app()->bind` 대응).

```python
from ninefruits.lms.connectors import NullConnector, connectors


class ScoringConnector(NullConnector):
    def final_scores(self, platform, course_id):
        return {"user-12": 87.5}


def test_imports_scores(...):
    with connectors().override("null", ScoringConnector()):
        ...
```

HTTP 커넥터 자체는 `respx`(httpx 가짜 응답)로 단위 테스트한다. 연동 흐름 전체의 예는 `tests/lms/test_lms.py`(이벤트, 명령, 대조, 점수 초안, 포털, RLS), API는 `tests/api/test_api.py`다. 실제 플랫폼 시험은 Docker Compose에 시험 인스턴스를 붙여(`compose.override.yaml`) 수동으로 한다.

## 4. 플랫폼이 부르는 API

플랫폼이 비동기로 처리하거나 점수를 밀어 보내는 경우를 위한 콜백이다. `lms.manage` 권한만 가진 서비스 계정을 만들고 토큰을 발급한다([ADR 0004-django](../porting/decisions/0004-django-api-tokens.md)).

```bash
uv run manage.py api_issue_token moodle-sync@example.ac.kr --days=365 --reason="Moodle 콜백" --actor=admin@example.ac.kr
```

| 요청 | 내용 |
|---|---|
| `GET /api/v1/lms/platforms/` , `GET /api/v1/lms/platforms/{code}/` | 플랫폼(코드, 이름, 드라이버, URL, 사용 여부). 인증 정보는 나오지 않는다 |
| `GET /api/v1/lms/platforms/{code}/course-links/?term=2026-FA&status=linked` | 강좌 연결(개설강좌 id·이름, 학기, 플랫폼 강좌 ID·URL, 상태, 마지막 동기화·오류). `?limit=`·`?offset=` |
| `POST /api/v1/lms/platforms/{code}/sync-results/` | 단계 결과: `{"log_id"?, "operation", "status", "message"?, "section_id"?, "external_course_id"?, "external_url"?}`. `operation`은 `course.sync`, `enrollment.add`, `enrollment.remove`, `reconcile`, `status`는 `succeeded`, `failed`, `skipped`. `log_id`가 있으면 대기 중인 기록을 마치고, 없으면 새 기록을 남긴다. 강좌 결과는 강좌 연결을 "연결됨"(플랫폼 ID·URL) 또는 "실패"(메시지)로 바꾼다 |
| `POST /api/v1/lms/platforms/{code}/scores/` | 최종 점수: `{"external_course_id": "...", "scores": {"<외부 사용자 ID>": 87.5}}`(0~100, 한 번에 5,000건까지). 동기화 기록 `grades.delivered`로 남고, 응답은 개설강좌 id, 점수 수, 수강생과 맞은 수. **저장되지 않는다**: 성적 입력의 **LMS 점수 불러오기**가 커넥터의 `final_scores`가 비어 있으면 가장 최근 전달분을 쓴다 |

요청은 `Authorization: Token <token>` 헤더로 보낸다. 토큰별 600회/분 제한(`integration`)이 있다. 스키마는 `/api/schema/`, 관리자는 `/api/docs/`(Swagger UI)에서 볼 수 있다.

## 5. 대상 플랫폼별 메모 (구현 시 대상 버전에서 검증할 것)

### Moodle (4.x)

- 인증: Web Services 토큰(사이트 관리 > 서버 > 웹 서비스), REST 프로토콜. 필요한 함수 권한: `core_course_create_courses`, `core_course_get_courses_by_field`, `core_user_create_users`, `core_user_get_users_by_field`, `enrol_manual_enrol_users`, `enrol_manual_unenrol_users`, `core_enrol_get_enrolled_users`, `gradereport_user_get_grade_items`(최종 점수).
- 엔드포인트: `POST {base}/webservice/rest/server.php?wstoken=…&wsfunction=…&moodlewsrestformat=json`.
- 매핑: 강좌 `shortname` = `{학기 코드}-{과목 코드}-{분반}`, `idnumber` = `sections.id`; 사용자 `username`/`idnumber` = 기관 이메일 / `users.id`. 역할 ID는 플랫폼 설정(기본 editingteacher=3, student=5)을 `options`에 둔다.
- 통합 로그인: Moodle OIDC 플러그인(auth_oidc) 또는 SAML2(auth_saml2)를 공용 IdP에 연결. 학사 시스템은 IdP가 아니므로 IdP를 따로 운영한다([관리자 매뉴얼 15장](manual/ko/admin/15-sign-in-methods.md)).
- 강좌 바로가기: `external_url` = `{base}/course/view.php?id={course id}`. LTI 1.3은 IdP와 같은 신원 체계가 있어야 의미가 있으므로 다음 단계.

### Open edX (Teak 이상)

- 인증: OAuth2 클라이언트(JWT), `{lms}/oauth2/access_token`. 강좌 생성은 Studio(CMS) API, 등록은 `POST {lms}/api/enrollment/v1/enrollment`, 명단은 `GET {lms}/api/enrollment/v1/enrollments?course_id=…`, 점수는 `GET {lms}/api/grades/v1/courses/{course_id}/`.
- 강좌 키 형식 `course-v1:{Org}+{Number}+{Run}`: `Org` = 기관 코드, `Number` = 과목 코드, `Run` = 학기 코드 + 분반.
- 사용자: 이메일로 매칭. 계정 자동 생성은 플랫폼 정책(`ALLOW_PUBLIC_ACCOUNT_CREATION`)에 따른다.

### 1EdTech OneRoster 1.2

- 명단 교환 표준. 플랫폼이 OneRoster 소비자를 지원하면 커넥터 대신 `reporting` 뷰(`students`, `section_enrollments`)를 내보내는 편이 단순하다. API `GET /api/v1/reports/{view}/`(`reports.view`, RLS 적용)로 읽거나, BI처럼 `app_reporting` 역할로 DB에서 직접 읽는다.

## 6. 운영

- 즉시 반영: 강좌 공개, 수강 확정, 수강 취소·철회 시 Celery 작업(`lms.sync_section`, `lms.sync_enrollment`, 3회 재시도). 실패는 **동기화 기록**에서 보고 **강좌 연결 > 다시 동기화**로 재시도한다. Flower에서 작업 상태를 본다.
- 야간 대조: `lms.reconcile`(beat, 02:30) = `lms_reconcile`. 플랫폼 명단과 학사 명단을 비교해 빠진 구성원을 추가하고 남은 구성원을 제거한다. 차이는 `reconcile` 기록의 `payload`(`missing`, `extra`)에 남는다. 대조 범위는 끝나지 않은 학기의 공개 강좌.
- 학기 시작 전 전체 밀어넣기: `uv run manage.py lms_sync {platform} --term={학기} --actor=...`(먼저 `--dry-run`).
- 인증 정보 교체: 플랫폼 수정 화면에서 새 값 입력(비워 두면 유지). 데이터 변경 기록에는 값이 남지 않는다(비밀 칼럼).
- 플랫폼 비활성화: 이벤트·대조가 멈춘다. 연결과 기록은 남는다.

## 7. 아직 없는 것

- 실제 커넥터(Moodle, Open edX), LTI 1.3 실행, 통합 로그인(IdP), 점수 자동 저장(초안 불러오기까지만), 콘텐츠·과제 연동(LMS 고유), 강좌 취소 시 플랫폼 강좌 정리, 플랫폼별 역할 매핑 화면(`options`에 둔다), API 토큰 관리 화면(명령과 API로 관리).
