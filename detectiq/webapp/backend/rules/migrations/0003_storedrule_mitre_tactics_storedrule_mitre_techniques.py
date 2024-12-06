# Generated by Django 4.2.16 on 2024-12-06 16:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rules", "0002_storedrule_package_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="storedrule",
            name="mitre_tactics",
            field=models.JSONField(blank=True, default=list, help_text="List of MITRE ATT&CK tactics"),
        ),
        migrations.AddField(
            model_name="storedrule",
            name="mitre_techniques",
            field=models.JSONField(blank=True, default=list, help_text="List of MITRE ATT&CK technique IDs"),
        ),
    ]