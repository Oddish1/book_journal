# Generated by Django 5.2 on 2025-04-22 16:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0016_alter_book_thumbnail_cover'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_public',
            field=models.BooleanField(default=False),
        ),
    ]
