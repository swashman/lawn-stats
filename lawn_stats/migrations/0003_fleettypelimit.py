# Generated by Django 4.2.11 on 2024-06-29 01:03

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lawn_stats", "0002_unknownaccount"),
    ]

    operations = [
        migrations.CreateModel(
            name="FleetTypeLimit",
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
                ("name", models.CharField(max_length=100)),
                ("limit", models.IntegerField()),
            ],
        ),
    ]