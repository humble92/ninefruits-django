"""Original migration 2026_10_22_000620_create_failed_import_rows_table. DDL replayed verbatim from db/schema/2026_10_22_000620_create_failed_import_rows_table.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0011_create_exports_table")]

    operations = [SqlFile.migration("schema/2026_10_22_000620_create_failed_import_rows_table.sql")]
