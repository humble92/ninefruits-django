"""Original migration 2026_10_23_001000_create_certificate_tables. DDL replayed verbatim from db/schema/2026_10_23_001000_create_certificate_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0038_fix_grade_scale_and_relative_evaluation")]

    operations = [SqlFile.migration("schema/2026_10_23_001000_create_certificate_tables.sql")]
