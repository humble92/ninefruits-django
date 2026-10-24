"""Original migration 2026_10_22_007200_raise_minimum_response_percent. DDL replayed verbatim from db/schema/2026_10_22_007200_raise_minimum_response_percent.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0036_enable_evaluation_row_level_security")]

    operations = [SqlFile.migration("schema/2026_10_22_007200_raise_minimum_response_percent.sql")]
