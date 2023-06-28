# Generated by Django 4.1.5 on 2023-04-28 18:09

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teammembers',
            name='team_member_uid',
            field=models.UUIDField(default=uuid.UUID('df7bdd0f-e5ef-11ed-aaa5-37ca8d677a21'), primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='weeklystatuses',
            name='weekly_status_uid',
            field=models.UUIDField(default=uuid.UUID('df7bdd18-e5ef-11ed-aaa5-37ca8d677a21'), primary_key=True, serialize=False),
        ),
    ]