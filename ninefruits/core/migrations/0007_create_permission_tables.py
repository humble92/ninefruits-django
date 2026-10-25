"""Original migration 2026_10_22_000200_create_permission_tables. DDL replayed verbatim from db/schema/2026_10_22_000200_create_permission_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0006_create_settings_table")]

    operations = [SqlFile.migration("schema/2026_10_22_000200_create_permission_tables.sql")]
