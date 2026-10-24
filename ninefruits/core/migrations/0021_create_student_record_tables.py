"""Original migration 2026_10_22_002200_create_student_record_tables. DDL replayed verbatim from db/schema/2026_10_22_002200_create_student_record_tables.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0020_add_person_and_identities_to_users")]

    operations = [SqlFile.migration("schema/2026_10_22_002200_create_student_record_tables.sql")]
