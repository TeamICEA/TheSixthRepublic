# Generated by Django 5.2.1 on 2025-06-05 16:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_alter_politicianreport_politicians_bottom_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stance',
            name='politician',
            field=models.ForeignKey(db_column='str_id', on_delete=django.db.models.deletion.CASCADE, related_name='stances', to='main.politician', to_field='str_id', verbose_name='국회의원'),
        ),
    ]
