# Ninefruits Django — working guide

Port of [ninefruits-laravel](https://github.com/humble92/ninefruits-laravel) v1.0.0 to Django.
The plan is `porting/porting-plan.md`; Django-specific decisions are `porting/decisions/`.
Documentation, reports and ADRs are written in Korean (like the original); code, comments,
identifiers and msgids are English.

## Environment (this workstation)

- Always: `export UV_SYSTEM_CERTS=1; unset UV_NATIVE_TLS` before `uv` commands. Run Python
  only through `uv run` (`uv run manage.py ...`, `uv run pytest ...`).
- Services on 127.0.0.1: PostgreSQL 18 (superuser `postgres`/`postgres`, roles `app_migrator`,
  `app_runtime`, `app_reporting` with password `secret`), Redis 8 (6379), Gotenberg 8 (3000).
  Dev database `ninefruits` (`uv run manage.py migrate`).
- Original source (read only): `/home/user/src-laravel`. A runnable copy with vendor installed:
  `/home/user/laravel-ref` (database `laravel_ref`, fully migrated). Run PHP there with
  `/home/user/env-tools/php php artisan ...` (env `LARAVEL_DB=<db>` to pick a database).
  Run original tests as an oracle: `/home/user/env-tools/laravel-test <your_unique_db> tests/Feature/...`.
- Reference schema: `porting/reference/schema-fingerprint.txt` (catalog fingerprint) and
  `porting/reference/laravel-schema.sql` (pg_dump) of the original.

## Running tests

- `DB_TEST_DATABASE=test_nf_<yourname> uv run pytest --reuse-db tests/<area>` — always use a
  test database name of your own when other agents may run tests at the same time.
- Tests live only in `tests/` as `test_*.py`. Fixtures: `tests/conftest.py` (`as_user`,
  `without_baseline`), factories in `tests/factories/<app>.py` (factory_boy).
- Fixtures are created as the system actor `system:test` (RLS allows it). Requests through the
  test client run as the signed-in user. Database policy tests use `without_baseline`.
- `tests/db/test_schema_equivalence.py` and `tests/db/test_model_schema.py` must always pass.

## Schema rule (ADR 0001-django) — read this before writing a model

The whole database schema already exists: `ninefruits/core/migrations/0001..0048` replay the
DDL that each original migration executed (`db/schema/*.sql`, `-- @apply` lines pull files
from `db/sql/`, which is the original `database/sql/` verbatim). Therefore:

1. Write the model to match the existing table exactly: `db_table`, column names
   (`db_column` where the Django name differs), `null`, `max_length`, types, FK targets.
   Look at `porting/reference/laravel-schema.sql` for the table.
2. Run `uv run manage.py makemigrations <app>`. The command is overridden: for Ninefruits apps
   it writes **state-only** migrations (`SeparateDatabaseAndState`) depending on the latest
   core migration. Never hand-write DDL in a domain app migration.
3. `tests/db/test_model_schema.py` fails if a model and its table disagree.
4. Unique/check/exclusion constraints and indexes already exist in the DB. You may declare
   them in `Meta` for documentation only if their names match exactly; otherwise omit them.
5. Generated columns (`effective_period` etc.): declare as `GeneratedField` only if you need to
   read them; otherwise leave them out of the model.
6. Tables in `audit.*` / `reporting.*`: `managed = False`, `db_table = 'audit"."activity_log'`.
7. Never change the schema. If the original behaviour truly needs a schema change, stop and
   report it.

Settings rows (spatie `settings` table: `group`, `name`, `payload` json, `locked`) are data:
each settings group gets a `RunPython` data migration in `ninefruits/settings/migrations/`
mirroring the original `database/settings/*.php` (locale values mapped `zh_CN` -> `zh-hans`).

## Conventions

- Layout per app: `models/` (or `models.py`), `enums.py`, `actions/`, `services/`, `events.py`,
  `listeners.py`, `tasks.py`, `policies.py`, `notifications.py`, `admin/`, `views/`, `forms.py`,
  `api/`, `management/commands/`, `templates/<app>/`, `locale/`.
- Business logic only in `actions/` (one class per original Action, `__call__` or `handle`,
  `transaction.atomic`, audit via `ninefruits.audit`). Admin, portal views, API and commands
  only call actions.
- Every manager offers `visible_to(user)` (`ninefruits.core.models.VisibleQuerySet`). Admin
  `get_queryset`, portal views and API viewsets go through it.
- Permissions: catalog names `resource.action` (`ninefruits.security.enums.Permission`),
  checked with `user.has_perm("people.view")` / `has_perm(perm, obj)`. Do not use Django's
  `auth.Permission` or `Group`.
- Admin: subclass `ninefruits.adminpanel.mixins.CatalogAdmin` (`permissions` mapping) and set
  `navigation_group = NavigationGroup.X` (`ninefruits.adminpanel.navigation`; default: the app's
  group); custom pages via `admin.site.register_view(route, view, name=, permission=,
  navigation_group=, label=)`. Portal pages extend `portal/base.html` (block `content`) and add
  menu items with `ninefruits.portal.menu.register(key, label, url_name, personas=/permission=)`.
- DB session context: `ninefruits.core.db.session_context()`; tasks inherit
  `ninefruits.core.tasks.SystemTask`; commands that change data inherit
  `ninefruits.core.commands.AuditedCommand`.
- Events: `ninefruits.core.events` (`dispatch`, `listen(..., after_commit=True)`).
- Commands: original `context:action` becomes `context_action`; every command has a
  `### \`context_action\`` entry in `docs/manual/{ko,en,zh_Hans,lo}/operations/commands.md`.
- Translations: gettext, msgid = English source text, `pgettext(<original group>, ...)` when the
  same English needs different translations. Per-app catalogs:
  `ninefruits/<app>/locale/{ko,zh_Hans,lo}/LC_MESSAGES/django.po` (global templates use
  `locale/`). Convert the original `lang/*` values with `tools/convert_translations.py`.
  `uv run manage.py i18n_missing --strict` must pass. Never run plain `makemessages` from an
  app directory without its own `locale/` (it rewrites the global catalog): create
  `ninefruits/<app>/locale/{ko,zh_Hans,lo}/LC_MESSAGES` first, or use
  `uv run manage.py i18n_makemessages` from the repo root. Fill from the original with
  `uv run python tools/convert_translations.py --fill --app <app>` (or `--group <g> --app <app>`).
  The tool writes a `msgctxt` (= original group) when an English text has different translations
  in the original; use the same context in code (`pgettext("common", "Language")`). `# key:`
  comments name the original keys. Translatable DB values: `ninefruits.i18n.fields`
  (`TranslatableJSONField`, `I18n`, `I18nSearchText`); guide: `docs/development/adding-a-language.md`. Language codes: `en`, `ko`, `zh-hans`,
  `lo`; translatable jsonb keys use the same codes.
- SQL: ORM and bound parameters only. Raw SQL must be a constant string with placeholders
  (`tools/checks/raw_sql.py` enforces this). Never `.extra()`.
- PII: never in `__repr__`, logs, serializers, or admin lists unmasked.
- Style: `uv run ruff format`, `uv run ruff check`. Type hints everywhere.
- Do not commit or push; the coordinating session commits each phase.
