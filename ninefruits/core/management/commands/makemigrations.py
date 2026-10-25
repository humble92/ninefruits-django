"""``makemigrations`` for Ninefruits apps writes **state-only** migrations.

The database schema is the original's DDL, replayed by ``core`` migrations from
``db/schema/`` (ADR 0001-django). Models of the domain apps describe that schema; their
migrations only record Django's model state, wrapped in ``SeparateDatabaseAndState`` and
depending on the latest ``core`` schema migration. A schema change is therefore two steps:
add SQL to ``db/schema/`` with a new ``core`` migration, then change the model and run
``makemigrations``. ``tests/db/test_model_schema.py`` fails when a model and the database
disagree."""

from typing import Any

from django.core.management.commands.makemigrations import Command as MakeMigrationsCommand
from django.db import migrations
from django.db.migrations.loader import MigrationLoader

STATE_ONLY_EXEMPT = {"core"}


def latest_core_migration() -> str:
    loader = MigrationLoader(None, ignore_no_migrations=True)
    return max(name for app, name in loader.disk_migrations if app == "core")


class Command(MakeMigrationsCommand):
    def write_migration_files(self, changes: dict[str, list[Any]], *args: Any, **kwargs: Any) -> None:
        core = latest_core_migration()
        for app_label, app_migrations in changes.items():
            if app_label in STATE_ONLY_EXEMPT or not self._is_ninefruits_app(app_label):
                continue
            for migration in app_migrations:
                operations = [op for op in migration.operations]
                if operations and not all(isinstance(op, migrations.SeparateDatabaseAndState) for op in operations):
                    migration.operations = [migrations.SeparateDatabaseAndState(state_operations=operations)]
                if ("core", core) not in migration.dependencies:
                    migration.dependencies.append(("core", core))
        super().write_migration_files(changes, *args, **kwargs)

    @staticmethod
    def _is_ninefruits_app(app_label: str) -> bool:
        from django.apps import apps

        return apps.get_app_config(app_label).name.startswith("ninefruits.")
