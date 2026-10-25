# 백업과 복구

- 대상: IT 운영자
- 관련: [설치](installation.md), [키 관리](security-keys.md), [감사 무결성](audit-and-maintenance.md)

## 백업 대상

| 대상 | 방법 | 주기(권장) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` 또는 PITR(WAL 보관) | 매일 전체 + WAL 연속 |
| 비공개 파일 저장소 (`PRIVATE_MEDIA_ROOT`, 기본 `storage/private`) | 스냅샷 또는 버전 관리 버킷 | DB와 같은 주기 |
| 환경 설정과 키 (`DJANGO_SECRET_KEY`, `PII_*`, DB 비밀번호) | 비밀 저장소 | 변경 시 |

DB와 파일 저장소는 같은 시점으로 복원할 수 있어야 한다(사진, 지원 서류, 증명서 PDF, 시험 증빙의 메타데이터가 DB `media` 테이블에 있다). Redis는 백업하지 않는다. 캐시, 잠금, 큐만 있고 세션은 DB(`django_session`)에도 저장된다. 예약 작업 목록(django-celery-beat)도 DB에 있고 beat가 시작할 때 `config/celery.py`에서 다시 맞춘다.

`staticfiles/`와 `static/dist/`는 빌드 산출물이므로 백업하지 않는다(`npm run build`, `collectstatic`으로 다시 만든다).

## DB 백업 예

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator`는 모든 스키마(`public`, `audit`, `reporting`, `util`)의 소유자이므로 이 계정으로 백업한다. 역할(`app_*`)은 클러스터 객체라 덤프에 들어가지 않는다. 복원 서버에서 [설치](installation.md) 2절의 역할 생성을 먼저 한다.

백업 전에 `uv run manage.py audit_verify_chain`을 실행해 두면 복원한 DB의 감사 체인을 같은 명령으로 비교할 수 있다.

## 복원 예

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

복원한 DB로 애플리케이션을 띄울 때는 `DB_DATABASE=ninefruits_restore`와 **백업 시점의 키**(`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, 그 사이에 교체했다면 `PII_PREVIOUS_KEYS`)를 넣는다. 다음 명령으로 상태를 맞춘다.

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # 코드와 스키마 버전이 같은지
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

`migrate --check`가 적용할 마이그레이션을 보고하면 백업이 현재 코드보다 오래된 것이다. 같은 버전의 코드로 복원하거나 `setup_install --force`로 올린다.

## 복구 훈련

분기마다 별도 서버에 복원하고 다음을 확인한다: 로그인, 개인정보 복호화(관리 화면 인물 상세의 **주민등록번호 보기**, 키 일치), 감사 기록 조회와 `audit_verify_chain`, 파일(사진, 증명서 PDF) 열람, 증명서 진위 확인 페이지. 훈련 결과(소요 시간, 문제)를 기록한다.
