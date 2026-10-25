"""Original migration 2026_10_22_007000_create_evaluation_tables. DDL replayed verbatim from db/schema/2026_10_22_007000_create_evaluation_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0034_add_evaluation_method_and_comparison_grades")]

    operations = [SqlFile.migration("schema/2026_10_22_007000_create_evaluation_tables.sql")]
