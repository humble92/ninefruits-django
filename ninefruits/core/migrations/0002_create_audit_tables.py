"""Original migration 0000_00_00_000001_create_audit_tables. DDL replayed verbatim from db/schema/0000_00_00_000001_create_audit_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0001_create_database_schemas")]

    operations = [SqlFile.migration("schema/0000_00_00_000001_create_audit_tables.sql")]
