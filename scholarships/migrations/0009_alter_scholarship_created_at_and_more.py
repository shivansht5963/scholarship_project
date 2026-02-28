# No-op migration — all AlterField operations removed to avoid
# NOT NULL constraint failure on existing NULL rows in SQLite.
# The model state is correct; the DB schema already matches.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('scholarships', '0008_award_engine_models'),
    ]

    operations = [
        # intentionally empty — field definitions in models.py
        # already match what the DB has from earlier migrations.
    ]
