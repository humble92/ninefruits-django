"""Original migration 2026_10_22_004300_create_section_tables. DDL replayed verbatim from db/schema/2026_10_22_004300_create_section_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0027_create_curriculum_requirement_tables")]

    operations = [SqlFile.migration("schema/2026_10_22_004300_create_section_tables.sql")]
