from django.db import migrations

from ninefruits.core.db import SqlFile

FILE = "2026_11_28_000100_add_program_scope_to_year_level_runs.sql"


class Migration(migrations.Migration):
    dependencies = [("core", "0052_create_year_level_progression_tables")]

    operations = [
        migrations.RunSQL(SqlFile.read(f"schema/{FILE}"), reverse_sql=SqlFile.read(f"schema/reverse/{FILE}")),
    ]
