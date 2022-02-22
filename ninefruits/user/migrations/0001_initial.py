# Generated by Django 4.0 on 2022-02-21 07:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='AbsentStudent',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('auth.user',),
        ),
        migrations.CreateModel(
            name='Applicant',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('auth.user',),
        ),
        migrations.CreateModel(
            name='Graduate',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('auth.user',),
        ),
        migrations.CreateModel(
            name='Professor',
            fields=[
            ],
            options={
                'ordering': ('first_name',),
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('auth.user',),
        ),
        migrations.CreateModel(
            name='Staff',
            fields=[
            ],
            options={
                'ordering': ('first_name',),
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('auth.user',),
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('auth.user',),
        ),
        migrations.CreateModel(
            name='TotalStudent',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('auth.user',),
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_no', models.CharField(blank=True, max_length=16, null=True)),
                ('profile_type', models.CharField(blank=True, choices=[('P', 'Professor'), ('F', 'Staff'), ('S', 'Student'), ('G', 'Graduate'), ('A', 'Applicant'), ('L', 'Student on a leave of absence')], max_length=1, null=True)),
                ('sex', models.CharField(blank=True, choices=[('M', 'Male'), ('F', 'Female'), ('N', 'Neutral')], max_length=1, null=True)),
                ('birth_date', models.DateField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='auth.user')),
            ],
        ),
    ]
