"""Joins the institution (i18n work) and security/authentication (security work) settings chains."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("appsettings", "0005_authentication_settings"),
        ("appsettings", "0006_lao_locale"),
    ]

    operations: list[migrations.operations.base.Operation] = []
