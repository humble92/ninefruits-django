# Generated by Django 4.0 on 2022-02-21 10:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='staff',
            options={'ordering': ('first_name',), 'verbose_name_plural': 'staff'},
        ),
    ]
