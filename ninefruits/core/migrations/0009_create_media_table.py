"""Original migration 2026_10_22_000500_create_media_table. DDL replayed verbatim from db/schema/2026_10_22_000500_create_media_table.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0008_create_features_table")]

    operations = [SqlFile.migration("schema/2026_10_22_000500_create_media_table.sql")]
