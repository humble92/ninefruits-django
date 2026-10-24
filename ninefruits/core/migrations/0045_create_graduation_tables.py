"""Original migration 2026_10_23_004000_create_graduation_tables. DDL replayed verbatim from db/schema/2026_10_23_004000_create_graduation_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0044_create_assessment_result_corrections")]

    operations = [SqlFile.migration("schema/2026_10_23_004000_create_graduation_tables.sql")]
