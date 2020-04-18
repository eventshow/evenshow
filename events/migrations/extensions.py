from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    run_before = [
        ('events', '0001_initial'),
    ]

    operations = [
        TrigramExtension(),
        UnaccentExtension(),
    ]
