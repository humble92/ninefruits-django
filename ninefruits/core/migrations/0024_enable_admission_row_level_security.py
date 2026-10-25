"""Original migration 2026_10_22_003100_enable_admission_row_level_security. DDL replayed verbatim from db/schema/2026_10_22_003100_enable_admission_row_level_security.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0023_create_admission_tables")]

    operations = [SqlFile.migration("schema/2026_10_22_003100_enable_admission_row_level_security.sql")]
