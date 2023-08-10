# Generated by Django 4.1.3 on 2023-07-14 18:56

import django.contrib.postgres.fields
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0005_alter_teammembers_team_member_uid_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MatVwOrgsAllIps',
            fields=[
                ('organizations_uid', models.UUIDField(primary_key=True, serialize=False)),
                ('cyhy_db_name', models.TextField(blank=True, null=True)),
                ('ip_addresses', django.contrib.postgres.fields.ArrayField(base_field=models.GenericIPAddressField(blank=True, null=True), blank=True, null=True, size=None)),
            ],
            options={
                'db_table': 'mat_vw_orgs_all_ips',
                'managed': False,
            },
        ),
        migrations.DeleteModel(
            name='VwOrgsAllIps',
        ),
        migrations.AlterField(
            model_name='teammembers',
            name='team_member_uid',
            field=models.UUIDField(default=uuid.UUID('343aaf37-2278-11ee-aaa7-37ca8d677a21'), primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='weeklystatuses',
            name='weekly_status_uid',
            field=models.UUIDField(primary_key=True, serialize=False),
        ),
    ]
