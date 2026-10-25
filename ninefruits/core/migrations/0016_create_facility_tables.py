"""Original migration 2026_10_22_001200_create_facility_tables. DDL replayed verbatim from db/schema/2026_10_22_001200_create_facility_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0015_create_organization_tables")]

    operations = [SqlFile.migration("schema/2026_10_22_001200_create_facility_tables.sql")]
