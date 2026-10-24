"""Original migration 2026_10_23_006000_add_audit_hash_chain. DDL replayed verbatim from db/schema/2026_10_23_006000_add_audit_hash_chain.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0047_create_lms_tables")]

    operations = [SqlFile.migration("schema/2026_10_23_006000_add_audit_hash_chain.sql")]
