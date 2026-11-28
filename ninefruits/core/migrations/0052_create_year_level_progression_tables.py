from django.db import migrations

from ninefruits.core.db import SqlFile

FILE = "2026_11_27_000200_create_year_level_progression_tables.sql"


class Migration(migrations.Migration):
    dependencies = [("core", "0051_use_codes_for_instructor_academic_titles")]

    operations = [
        migrations.RunSQL(SqlFile.read(f"schema/{FILE}"), reverse_sql=SqlFile.read(f"schema/reverse/{FILE}")),
    ]
