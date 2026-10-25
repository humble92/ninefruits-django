"""Original migration 2026_10_22_002000_create_people_tables. DDL replayed verbatim from db/schema/2026_10_22_002000_create_people_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0018_create_course_category_and_grade_scale_tables")]

    operations = [SqlFile.migration("schema/2026_10_22_002000_create_people_tables.sql")]
