"""Original migration 2026_10_22_000100_create_settings_table. DDL replayed verbatim from db/schema/2026_10_22_000100_create_settings_table.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0005_create_jobs_table")]

    operations = [SqlFile.migration("schema/2026_10_22_000100_create_settings_table.sql")]
