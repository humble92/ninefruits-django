"""Original migration 2026_10_23_005000_create_lms_tables. DDL replayed verbatim from db/schema/2026_10_23_005000_create_lms_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0046_create_reporting_views")]

    operations = [SqlFile.migration("schema/2026_10_23_005000_create_lms_tables.sql")]
