"""Original migration 2026_10_23_000100_fix_grade_scale_and_relative_evaluation. DDL replayed verbatim from db/schema/2026_10_23_000100_fix_grade_scale_and_relative_evaluation.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0037_raise_minimum_response_percent")]

    operations = [SqlFile.migration("schema/2026_10_23_000100_fix_grade_scale_and_relative_evaluation.sql")]
