"""Original migration 2026_10_22_003000_create_admission_tables. DDL replayed verbatim from db/schema/2026_10_22_003000_create_admission_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0022_enable_people_row_level_security")]

    operations = [SqlFile.migration("schema/2026_10_22_003000_create_admission_tables.sql")]
