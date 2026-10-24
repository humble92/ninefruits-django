# 0001-django. 스키마는 원본 DDL을 그대로 재생하고, 도메인 앱 마이그레이션은 상태 전용으로 둔다

- 상태: 채택 (2026-10-24, Phase 0)
- 관련: [이식 계획 2절 원칙 3, 5.3절, 13.5절 완료 기준 6](../porting-plan.md)

## 배경

계획은 DB 스키마(테이블, 컬럼, 제약, 함수, 트리거, RLS 정책, 뷰)를 원본과 **동일하게** 유지하고 `pg_dump` 비교로 확인하라고 한다. Django ORM이 만드는 DDL은 다음 점에서 원본과 같아질 수 없다.

- 외래 키 제약 이름을 지정할 수 없다(Django는 `<table>_<col>_<hash>_fk_...`, 원본은 `<table>_<col>_foreign`).
- `db_index=True` 인덱스와 unique 제약 이름도 해시 기반이다.
- 기본 키는 identity 열(원본은 `bigserial`), `timestamp(0)` 정밀도, `varchar(255)` 등 세부 타입이 다르다.

## 결정

1. 원본 v1.0.0의 마이그레이션 48개를 PostgreSQL 18.6에서 실제로 실행하면서 각 마이그레이션이 보낸 SQL을 기록했다(`db/schema/*.sql`). 원본이 `SqlFile::apply()`로 적용한 파일은 `-- @apply <경로>` 표시로 남기고, 그 파일 자체는 `db/sql/`(원본 `database/sql/` 그대로)에서 읽는다.
2. `ninefruits/core/migrations/0001~0048`이 이 파일들을 원본과 같은 순서로 `RunSQL` 한다. 역할 이름이 기본값과 다르면 `"app_runtime"`, `"app_reporting"`만 바꾼다.
3. 도메인 앱의 모델은 이 스키마를 기술한다. 마이그레이션은 `SeparateDatabaseAndState(state_operations=...)`로 Django 상태만 기록하며, 재정의한 `makemigrations` 명령이 자동으로 감싸고 최신 core 마이그레이션에 의존시킨다.
4. 설정 그룹의 행(`settings` 테이블)은 스키마가 아니라 데이터이므로 `settings` 앱의 `RunPython` 데이터 마이그레이션으로 옮긴다(로케일 값 `zh_CN` → `zh-hans`).
5. 검증
   - `tests/db/test_schema_equivalence.py`: 카탈로그 지문(열, 기본값, 제약, 인덱스, 트리거, 정책, 함수 정의, 뷰 정의, 권한, 기본 권한, 확장)을 원본에서 뜬 `porting/reference/schema-fingerprint.txt`와 비교한다. `pg_dump` 바이너리 버전에 의존하지 않도록 카탈로그를 직접 읽는다. 사람이 보는 용도로 `porting/reference/laravel-schema.sql`(pg_dump)도 둔다.
   - `tests/db/test_model_schema.py`: 모든 모델 필드가 실제 열과 이름, 타입 계열, NULL 허용, 길이에서 일치하는지 확인한다. 상태 전용 마이그레이션이 DB와 어긋나는 것을 막는다.

## 결과

- 계획 7.1절이 예상한 "사용자 테이블 차이"가 없어진다. `users`의 Fortify 2단계 열(`two_factor_secret`, `two_factor_recovery_codes`, `two_factor_confirmed_at`)과 `remember_token`은 남아 있으나 쓰지 않는다. TOTP와 복구 코드는 allauth `mfa_authenticator` 테이블에 있다. `email_mfa_enabled_at`, `mfa_grace_started_at`, `failed_login_count`, `locked_until`, `last_login_at`(Django `last_login`의 `db_column`)은 그대로 쓴다.
- Laravel 프레임워크 테이블(`cache`, `cache_locks`, `jobs`, `job_batches`, `failed_jobs`, `sessions`, `password_reset_tokens`, `features`, `model_has_roles`, `model_has_permissions`)도 같은 이름으로 존재한다. Django가 쓰지 않는 것은 비워 두며, `pg_restore`로 원본 데이터를 옮길 때 충돌하지 않는다. 원본의 `migrations` 테이블만 없다.
- Django 자체 테이블(`django_*`, `auth_*`, `account_*`, `mfa_*`, `socialaccount_*`, `knox_*`, `django_celery_beat_*`)은 비교에서 뺀다.
- 스키마 변경 절차: `db/schema/`에 SQL 파일과 core 마이그레이션을 추가한 뒤 모델을 고치고 `makemigrations`를 실행한다. 원본과의 동일성이 깨지므로 이식 완료 전까지는 하지 않는다.
- 단점: 모델의 `Meta.constraints`/`indexes`는 문서 용도이며 Django가 만들지 않는다. 모델만 고치면 DB가 바뀐다고 착각할 수 있으므로 `makemigrations` 도움말과 `CLAUDE.md`에 적었다.

## 검토한 대안

| 대안 | 기각 이유 |
|---|---|
| ORM DDL + 정규화된 비교(이름 무시) | 제약·인덱스 이름이 다르면 `pg_restore`와 원본 SQL 자산(정책·뷰가 이름을 참조하는 곳)이 깨진다. "동일" 요구를 충족하지 못한다 |
| 원본 Blueprint를 손으로 SQL로 옮김 | 오류 가능성이 크고 검증 수단이 없다. 실제 실행 기록이 더 정확하다 |
