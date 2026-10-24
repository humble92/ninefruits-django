"""Original migration 2026_10_22_001300_create_term_tables. DDL replayed verbatim from db/schema/2026_10_22_001300_create_term_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0016_create_facility_tables")]

    operations = [SqlFile.migration("schema/2026_10_22_001300_create_term_tables.sql")]
