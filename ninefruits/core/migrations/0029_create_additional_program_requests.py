"""Original migration 2026_10_22_004400_create_additional_program_requests. DDL replayed verbatim from db/schema/2026_10_22_004400_create_additional_program_requests.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0028_create_section_tables")]

    operations = [SqlFile.migration("schema/2026_10_22_004400_create_additional_program_requests.sql")]
