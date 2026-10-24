# 원본 스키마 기준 자료

- `schema-fingerprint.txt`: 원본 v1.0.0 마이그레이션을 PostgreSQL 18.6 빈 DB에 실행한 뒤 `ninefruits.core.schema.fingerprint()`로 뜬 카탈로그 지문. `tests/db/test_schema_equivalence.py`가 비교한다.
- `laravel-schema.sql`: 같은 DB의 `pg_dump --schema-only --no-owner --no-privileges`. 사람이 읽는 용도.

다시 만드는 방법(원본 저장소에서):

1. `create_roles.sql`, `prepare_database.sql`로 빈 DB를 준비하고 `php artisan migrate`.
2. `uv run python -c` 로 `fingerprint(cursor)`를 슈퍼유저 연결에서 실행해 파일로 쓴다.

`db/schema/*.sql`은 원본 마이그레이션 실행 중 `DB::listen`으로 기록한 SQL이다. `SqlFile::apply()` 호출은 `-- @apply` 표시로 바꾸었고 설정 데이터 마이그레이션(`database/settings`)은 제외했다.
