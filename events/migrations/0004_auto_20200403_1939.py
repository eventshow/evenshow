# Generated by Django 3.0.4 on 2020-04-03 17:39

from django.db import migrations, models
import django.db.models.deletion
import events.models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0003_auto_20200403_1733'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='category',
            field=models.ForeignKey(on_delete=models.SET(events.models.get_default_category), related_name='category_events', to='events.Category'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='picture',
            field=models.URLField(blank=True, default='https://i.imgur.com/smMeZJA.png', null=True, verbose_name='Picture url'),
        ),
        migrations.AlterField(
            model_name='rating',
            name='event',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ratings', to='events.Event'),
        ),
    ]
