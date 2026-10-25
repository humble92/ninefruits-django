"""Original migration 2026_10_22_004100_create_course_tables. DDL replayed verbatim from db/schema/2026_10_22_004100_create_course_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0025_create_term_sessions")]

    operations = [SqlFile.migration("schema/2026_10_22_004100_create_course_tables.sql")]
