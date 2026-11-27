"""Replay the Laravel academic title code migration, using Django locale keys for labels."""

from django.db import migrations

from ninefruits.core.db import SqlFile


class Migration(migrations.Migration):
    dependencies = [("core", "0050_job_batches_state")]

    operations = [
        migrations.RunSQL(
            SqlFile.read("schema/2026_11_27_000100_use_codes_for_instructor_academic_titles.sql"),
            reverse_sql=SqlFile.read("schema/reverse/2026_11_27_000100_use_codes_for_instructor_academic_titles.sql"),
        )
    ]
