"""Original migration 0001_01_01_000000_create_users_table. DDL replayed verbatim from db/schema/0001_01_01_000000_create_users_table.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0002_create_audit_tables")]

    operations = [SqlFile.migration("schema/0001_01_01_000000_create_users_table.sql")]
