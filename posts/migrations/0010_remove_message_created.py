# Generated by Django 2.2.6 on 2020-11-11 10:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0009_message'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='message',
            name='created',
        ),
    ]
