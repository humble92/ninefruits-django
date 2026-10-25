"""Original migration 2026_10_23_004100_create_reporting_views. DDL replayed verbatim from db/schema/2026_10_23_004100_create_reporting_views.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0045_create_graduation_tables")]

    operations = [SqlFile.migration("schema/2026_10_23_004100_create_reporting_views.sql")]
