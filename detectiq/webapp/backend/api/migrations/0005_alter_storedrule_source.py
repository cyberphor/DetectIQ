# Generated by Django 4.2.16 on 2024-11-25 02:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_storedrule_source"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storedrule",
            name="source",
            field=models.CharField(
                choices=[
                    ("DetectIQ", "DetectIQ"),
                    ("SigmaHQ", "SigmaHQ"),
                    ("YARA-Forge", "YARA-Forge"),
                    ("Snort3 Community", "Snort3 Community"),
                ],
                default="DetectIQ",
                max_length=50,
            ),
        ),
    ]
