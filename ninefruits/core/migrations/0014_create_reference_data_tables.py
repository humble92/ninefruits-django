"""Original migration 2026_10_22_001000_create_reference_data_tables. DDL replayed verbatim from db/schema/2026_10_22_001000_create_reference_data_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0013_create_notifications_table")]

    operations = [SqlFile.migration("schema/2026_10_22_001000_create_reference_data_tables.sql")]
