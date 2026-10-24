"""Django only (not in the original): django_migrations is created before 0001 sets the default
privileges, so the runtime role gets read access explicitly (runserver and makemigrations read
it). Django's own tables are excluded from the schema comparison."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("core", "0048_add_audit_hash_chain")]

    operations = [migrations.RunSQL('GRANT SELECT ON django_migrations TO "app_runtime"', migrations.RunSQL.noop)]
