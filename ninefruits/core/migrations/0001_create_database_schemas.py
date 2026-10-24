"""Original migration 0000_00_00_000000_create_database_schemas. DDL replayed verbatim from db/schema/0000_00_00_000000_create_database_schemas.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = []

    operations = [SqlFile.migration("schema/0000_00_00_000000_create_database_schemas.sql")]
