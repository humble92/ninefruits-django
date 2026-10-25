"""Original migration 2026_10_22_002100_add_person_and_identities_to_users. DDL replayed verbatim from db/schema/2026_10_22_002100_add_person_and_identities_to_users.sql (ADR 0001-django)."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0019_create_people_tables")]

    operations = [SqlFile.migration("schema/2026_10_22_002100_add_person_and_identities_to_users.sql")]
