"""Django only: the model state of ``job_batches`` (created by 0005 from the original's jobs
migration) for ``ninefruits.core.batches.JobBatch``. State only; the table exists."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0049_grant_django_migrations")]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="JobBatch",
                    fields=[
                        ("id", models.CharField(max_length=255, primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=255)),
                        ("total_jobs", models.IntegerField()),
                        ("pending_jobs", models.IntegerField()),
                        ("failed_jobs", models.IntegerField()),
                        ("failed_job_ids", models.TextField()),
                        ("options", models.TextField(blank=True, null=True)),
                        ("cancelled_at", models.IntegerField(blank=True, null=True)),
                        ("created_at", models.IntegerField()),
                        ("finished_at", models.IntegerField(blank=True, null=True)),
                    ],
                    options={"db_table": "job_batches", "ordering": ["-created_at"]},
                ),
            ]
        )
    ]
