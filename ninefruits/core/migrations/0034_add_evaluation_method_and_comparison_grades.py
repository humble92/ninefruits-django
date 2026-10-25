"""Original migration 2026_10_22_006200_add_evaluation_method_and_comparison_grades. DDL replayed verbatim from db/schema/2026_10_22_006200_add_evaluation_method_and_comparison_grades.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0033_enable_grading_row_level_security")]

    operations = [SqlFile.migration("schema/2026_10_22_006200_add_evaluation_method_and_comparison_grades.sql")]
