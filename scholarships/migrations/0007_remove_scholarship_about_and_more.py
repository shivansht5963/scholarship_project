# scholarships/migrations/0007_remove_scholarship_about_and_more.py
#
# REWRITTEN: Complete migration from old schema (after 0006 no-op) to new schema.
#
# DB state coming in (from 0005):
#   Existing fields: name(CharField unique), organization(CharField),
#     source_url, deadline(DateTimeField), award_amount, details, is_active,
#     is_verified, finder_karma_awarded, found_by_student,
#     about, award_per_student, custom_essay_question, demographic_focus(JSONField),
#     disbursement_method, distribution_logic, escrow_status, logo, max_family_income,
#     max_winners, min_academic_score, min_karma_required, razorpay_order_id,
#     razorpay_payment_id, streams, target_education_level, total_budget(DecimalField),
#     verification_strictness
#   Existing models: ScholarshipEscrowLedger
#
# This migration:
#   STEP 1 — Add all new fields that don't exist yet
#   STEP 2 — Remove old fields being replaced
#   STEP 3 — Alter existing fields to new types/options
#   STEP 4 — Delete old ScholarshipEscrowLedger, create ScholarshipFunding

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scholarships', '0006_scholarship_full_overhaul'),
        ('users', '0004_studentprofile_karma_rank_and_more'),
    ]

    operations = [

        # ══════════════════════════════════════════════════════════════════
        # STEP 1 — Add new fields (these do NOT exist in DB yet)
        # ══════════════════════════════════════════════════════════════════

        migrations.AddField(
            model_name='scholarship',
            name='title',
            field=models.CharField(blank=True, max_length=255, verbose_name='Scholarship Title'),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='org_profile',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='scholarships',
                to='users.organizationprofile',
                verbose_name='Organization',
            ),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='description',
            field=models.TextField(blank=True, verbose_name='About the Scholarship (HTML allowed)'),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='education_level',
            field=models.CharField(
                choices=[
                    ('HIGH_SCHOOL', 'High School (9th–12th)'),
                    ('DIPLOMA',     'Diploma'),
                    ('UG',          'Undergraduate (B.Tech / BA / B.Sc etc.)'),
                    ('PG',          'Postgraduate (M.Tech / MBA / M.Sc etc.)'),
                    ('PHD',         'Doctorate / Ph.D'),
                    ('ANY',         'Any Level'),
                ],
                default='ANY', max_length=20, verbose_name='Target Education Level',
            ),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='courses',
            field=models.TextField(
                blank=True, default='[]',
                help_text='JSON list of eligible courses/streams. Leave "[]" for any.',
            ),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='min_percentage',
            field=models.DecimalField(
                blank=True, null=True,
                max_digits=5, decimal_places=2,
                verbose_name='Minimum Academic Score (%/CGPA)',
            ),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='distribution_type',
            field=models.CharField(
                choices=[('FIXED', 'Fixed Amount per Winner'), ('DYNAMIC', 'Proportional / Dynamic Allocation')],
                default='FIXED', max_length=10, verbose_name='Distribution Logic',
            ),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='fixed_amount',
            field=models.PositiveIntegerField(
                blank=True, null=True,
                help_text='Required when distribution type is FIXED',
                verbose_name='Fixed Amount per Winner (₹)',
            ),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='num_winners',
            field=models.PositiveIntegerField(
                blank=True, null=True,
                help_text='How many students get selected',
                verbose_name='Number of Winners',
            ),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='min_karma',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Only students with ≥ this karma can apply',
                verbose_name='Minimum Karma Points Required',
            ),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='essay_question',
            field=models.TextField(
                blank=True,
                help_text="e.g. 'Why do you need this scholarship?'",
                verbose_name='Custom Essay / Question (Optional)',
            ),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='is_funded',
            field=models.BooleanField(
                default=False,
                help_text='True once Razorpay payment is verified',
            ),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='last_updated',
            field=models.DateTimeField(auto_now=True, null=True),
        ),

        # ══════════════════════════════════════════════════════════════════
        # STEP 2 — Remove old/renamed fields
        # ══════════════════════════════════════════════════════════════════

        migrations.RemoveField(model_name='scholarship', name='about'),
        migrations.RemoveField(model_name='scholarship', name='award_per_student'),
        migrations.RemoveField(model_name='scholarship', name='custom_essay_question'),
        migrations.RemoveField(model_name='scholarship', name='distribution_logic'),
        migrations.RemoveField(model_name='scholarship', name='escrow_status'),
        migrations.RemoveField(model_name='scholarship', name='max_winners'),
        migrations.RemoveField(model_name='scholarship', name='min_academic_score'),
        migrations.RemoveField(model_name='scholarship', name='min_karma_required'),
        migrations.RemoveField(model_name='scholarship', name='name'),
        migrations.RemoveField(model_name='scholarship', name='razorpay_order_id'),
        migrations.RemoveField(model_name='scholarship', name='razorpay_payment_id'),
        migrations.RemoveField(model_name='scholarship', name='streams'),
        migrations.RemoveField(model_name='scholarship', name='target_education_level'),

        # ══════════════════════════════════════════════════════════════════
        # STEP 3 — Alter existing fields to new type/options
        # ══════════════════════════════════════════════════════════════════

        migrations.AlterField(
            model_name='eligibilitycriteria',
            name='comparison_operator',
            field=models.CharField(
                choices=[('GT', '>'), ('LT', '<'), ('EQ', '='), ('IN', 'IN')],
                default='GT', max_length=2,
            ),
        ),
        migrations.AlterField(
            model_name='eligibilitycriteria',
            name='criterion_type',
            field=models.CharField(
                help_text="e.g. 'MIN_INCOME', 'MAX_AGE', 'MIN_GPA', 'STATE'",
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name='scholarship',
            name='award_amount',
            field=models.CharField(
                blank=True,
                help_text='[Legacy] Free-text award amount. Use total_budget instead.',
                max_length=50,
            ),
        ),
        # demographic_focus: was JSONField, now TextField storing JSON string
        migrations.AlterField(
            model_name='scholarship',
            name='demographic_focus',
            field=models.TextField(
                blank=True, default='[]',
                help_text='JSON list of demographic targets. Leave "[]" for all.',
            ),
        ),
        migrations.AlterField(
            model_name='scholarship',
            name='details',
            field=models.TextField(blank=True, help_text='[Legacy] Use description instead.'),
        ),
        migrations.AlterField(
            model_name='scholarship',
            name='found_by_student',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='found_scholarships',
                to='users.studentprofile',
            ),
        ),
        migrations.AlterField(
            model_name='scholarship',
            name='is_active',
            field=models.BooleanField(
                default=False,
                help_text='Becomes True only after payment is confirmed',
            ),
        ),
        # organization: was FK to OrganizationProfile in 0004 — can't alter FK to CharField in SQLite.
        # Remove the FK column and add a new plain CharField.
        migrations.RemoveField(model_name='scholarship', name='organization'),
        migrations.AddField(
            model_name='scholarship',
            name='organization',
            field=models.CharField(
                blank=True, default='',
                help_text='[Legacy] Organization name as string. Use org_profile FK instead.',
                max_length=255,
            ),
        ),
        # total_budget: was DecimalField(max_digits=12) in 0004, now PositiveIntegerField.
        # Remove + re-add since SQLite can't alter column type directly.
        migrations.RemoveField(model_name='scholarship', name='total_budget'),
        migrations.AddField(
            model_name='scholarship',
            name='total_budget',
            field=models.PositiveIntegerField(
                blank=True, null=True, default=None,
                help_text='Full amount the organization deposits into escrow (INR)',
                verbose_name='Total Budget (₹)',
            ),
        ),
        # verification_strictness: choices update
        migrations.AlterField(
            model_name='scholarship',
            name='verification_strictness',
            field=models.CharField(
                choices=[
                    ('STANDARD', 'Standard – Manual Upload'),
                    ('STRICT',   'Strict – DigiLocker / Govt API Verified'),
                ],
                default='STANDARD', max_length=10, verbose_name='Verification Strictness',
            ),
        ),
        migrations.AlterField(
            model_name='requireddocument',
            name='document_name',
            field=models.CharField(
                max_length=100,
                choices=[
                    ('income_certificate',   'Income Certificate'),
                    ('marksheet',            'Previous Year Marksheet'),
                    ('college_id',           'College ID / Bonafide Certificate'),
                    ('aadhaar',              'Aadhaar Card'),
                    ('caste_certificate',    'Caste Certificate'),
                    ('bank_passbook',        'Bank Passbook'),
                    ('disability_cert',      'Disability Certificate'),
                    ('domicile_certificate', 'Domicile Certificate'),
                    ('photo',                'Passport Size Photo'),
                ],
                help_text='Identifier key for the document type',
            ),
        ),
        migrations.AddField(
            model_name='requireddocument',
            name='verification_strictness',
            field=models.CharField(
                choices=[
                    ('STANDARD', 'Standard – Manual Upload'),
                    ('STRICT',   'Strict – DigiLocker / Govt API Verified'),
                ],
                default='STANDARD', max_length=10,
                verbose_name='Verification Method for this document',
            ),
        ),

        # ══════════════════════════════════════════════════════════════════
        # STEP 4 — Delete old ledger, create new ScholarshipFunding
        # ══════════════════════════════════════════════════════════════════

        migrations.DeleteModel(name='ScholarshipEscrowLedger'),

        migrations.CreateModel(
            name='ScholarshipFunding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('razorpay_order_id',   models.CharField(blank=True, max_length=100)),
                ('razorpay_payment_id', models.CharField(blank=True, max_length=100)),
                ('razorpay_signature',  models.CharField(blank=True, max_length=255)),
                ('amount_paise', models.PositiveIntegerField(
                    default=0, help_text='Amount in paise (INR × 100)',
                )),
                ('status', models.CharField(
                    choices=[
                        ('PENDING',   'Pending Payment'),
                        ('PAID',      'Paid – In Escrow'),
                        ('DISBURSED', 'Disbursed to Winners'),
                        ('REFUNDED',  'Refunded'),
                    ],
                    default='PENDING', max_length=10,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at',    models.DateTimeField(blank=True, null=True)),
                ('scholarship', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='funding',
                    to='scholarships.scholarship',
                )),
            ],
        ),

        migrations.AlterModelOptions(
            name='scholarship',
            options={'ordering': ['-created_at']},
        ),
    ]
