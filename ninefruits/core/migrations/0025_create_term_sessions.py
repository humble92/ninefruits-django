"""Original migration 2026_10_22_004000_create_term_sessions. DDL replayed verbatim from db/schema/2026_10_22_004000_create_term_sessions.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0024_enable_admission_row_level_security")]

    operations = [SqlFile.migration("schema/2026_10_22_004000_create_term_sessions.sql")]
