# Generated by Django 5.2 on 2025-04-07 19:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0006_alter_covers_image_alter_covers_image_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authors',
            name='birth_date',
            field=models.DateField(null=True),
        ),
    ]
