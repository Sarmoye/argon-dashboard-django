# Generated by Django 3.2.6 on 2025-01-30 08:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis', '0002_alter_ficheerreur_timestamp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ficheerreur',
            name='charge_systeme',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ficheerreur',
            name='impact_financier',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
