# Generated by Django 3.2.16 on 2022-11-24 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0013_follow'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='follow',
            constraint=models.UniqueConstraint(fields=('author', 'user'), name='follow_constraints'),
        ),
    ]
