# Generated by Django 4.2.11 on 2024-06-25 00:24

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lawn_stats", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnknownAccount",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("account_name", models.CharField(max_length=255, unique=True)),
                ("user_id", models.IntegerField(blank=True, null=True)),
            ],
        ),
    ]
