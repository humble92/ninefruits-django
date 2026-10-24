"""Original migration 2026_10_23_003100_create_assessment_result_corrections. DDL replayed verbatim from db/schema/2026_10_23_003100_create_assessment_result_corrections.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0043_create_attendance_tables")]

    operations = [SqlFile.migration("schema/2026_10_23_003100_create_assessment_result_corrections.sql")]
