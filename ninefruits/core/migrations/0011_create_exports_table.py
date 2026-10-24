"""Original migration 2026_10_22_000610_create_exports_table. DDL replayed verbatim from db/schema/2026_10_22_000610_create_exports_table.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0010_create_imports_table")]

    operations = [SqlFile.migration("schema/2026_10_22_000610_create_exports_table.sql")]
