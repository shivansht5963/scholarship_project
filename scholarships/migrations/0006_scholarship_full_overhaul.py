# scholarships/migrations/0006_scholarship_full_overhaul.py
#
# REPLACED: Our handwritten migration conflicted with fields already added
# in 0004. This file is now a no-op placeholder so that 0007 (the correct
# Django auto-generated migration) can depend on it cleanly.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('scholarships', '0005_alter_scholarship_options'),
    ]

    operations = [
        # Intentionally empty — see 0007 for the actual schema changes.
    ]
