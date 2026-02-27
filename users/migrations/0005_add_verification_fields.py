from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_studentprofile_karma_rank_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentdocument',
            name='verification_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending Verification'),
                    ('verified', 'Verified'),
                    ('failed', 'Verification Failed'),
                    ('not_applicable', 'Not Required'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='studentdocument',
            name='verification_result',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
