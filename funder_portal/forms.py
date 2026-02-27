# funder_portal/forms.py

from django import forms
from scholarships.models import Scholarship, DOCUMENT_CHOICES


class FunderScholarshipForm(forms.ModelForm):
    """[Legacy] Kept as fallback. New flow uses the 4 step forms below."""

    required_documents = forms.MultipleChoiceField(
        choices=DOCUMENT_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Required Documents',
        help_text='Select which documents students must upload for this scholarship'
    )

    class Meta:
        model = Scholarship
        fields = [
            'title',        # was 'name'
            'organization', # legacy CharField still exists
            'source_url',
            'deadline',
            'award_amount',
            'details',
            'is_active',
        ]
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'details':  forms.Textarea(attrs={'rows': 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            from scholarships.models import RequiredDocument
            existing_docs = RequiredDocument.objects.filter(
                scholarship=self.instance
            ).values_list('document_name', flat=True)
            self.fields['required_documents'].initial = list(existing_docs)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — The Basics
# ─────────────────────────────────────────────────────────────────────────────

class Step1BasicsForm(forms.ModelForm):
    class Meta:
        model = Scholarship
        fields = ['title', 'logo', 'description', 'deadline']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 6,
                'id': 'id_description',
                'placeholder': 'Tell students why you are giving this scholarship and the impact you want to make...'
            }),
            'deadline': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Future Innovators Tech Grant 2026'}),
        }
        labels = {
            'title':       'Scholarship Title',
            'logo':        'Organization Logo',
            'description': 'About the Scholarship',
            'deadline':    'Application Deadline',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make deadline format compatible
        self.fields['deadline'].input_formats = ['%Y-%m-%dT%H:%M']


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Eligibility Criteria
# ─────────────────────────────────────────────────────────────────────────────

DEMOGRAPHIC_CHOICES = [
    ('women',    'Women / Girls'),
    ('sc',       'SC Category'),
    ('st',       'ST Category'),
    ('obc',      'OBC Category'),
    ('ews',      'EWS (Economically Weaker Section)'),
    ('disabled', 'Persons with Disability'),
    ('tier2',    'Tier-2 / Tier-3 City Residents'),
    ('rural',    'Rural / Village Background'),
    ('minority', 'Minority Communities'),
]

class Step2EligibilityForm(forms.Form):
    """Not a ModelForm — we handle JSON fields manually in the view."""

    from scholarships.models import EDUCATION_LEVEL_CHOICES  # local import for choices

    education_level = forms.ChoiceField(
        choices=[('', '— Select Level —')] + [
            ('HIGH_SCHOOL', 'High School (9th–12th)'),
            ('DIPLOMA', 'Diploma'),
            ('UG', 'Undergraduate (B.Tech / BA / B.Sc etc.)'),
            ('PG', 'Postgraduate (M.Tech / MBA / M.Sc etc.)'),
            ('PHD', 'Doctorate / Ph.D'),
            ('ANY', 'Any Level'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Target Education Level'
    )
    courses_raw = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. B.Tech, MBBS, BA — comma separated',
            'id': 'id_courses_raw'
        }),
        label='Specific Courses / Streams',
        help_text='Leave blank to allow all courses.'
    )
    max_family_income = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'placeholder': 'e.g. 800000'}),
        label='Max Family Annual Income (₹)',
        help_text='Leave blank for no income limit.'
    )
    min_percentage = forms.DecimalField(
        required=False,
        max_digits=5, decimal_places=2,
        min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={'placeholder': 'e.g. 75.00', 'step': '0.01'}),
        label='Minimum Academic Score (% or CGPA)',
        help_text='Leave blank for no minimum requirement.'
    )
    demographic_focus = forms.MultipleChoiceField(
        choices=DEMOGRAPHIC_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Demographic Focus (Optional)',
        help_text='Check all groups you want to prioritize. Leave blank for everyone.'
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Financials & Distribution
# ─────────────────────────────────────────────────────────────────────────────

class Step3FinancialsForm(forms.ModelForm):
    class Meta:
        model = Scholarship
        fields = ['total_budget', 'distribution_type', 'fixed_amount', 'num_winners', 'disbursement_method']
        widgets = {
            'total_budget'     : forms.NumberInput(attrs={'placeholder': 'e.g. 10000', 'min': '100'}),
            'fixed_amount'     : forms.NumberInput(attrs={'placeholder': 'e.g. 2000', 'min': '1'}),
            'num_winners'      : forms.NumberInput(attrs={'placeholder': 'e.g. 5', 'min': '1'}),
            'distribution_type': forms.RadioSelect(),
            'disbursement_method': forms.RadioSelect(),
        }
        labels = {
            'total_budget'       : 'Total Budget to Deposit (₹)',
            'distribution_type'  : 'Distribution Logic',
            'fixed_amount'       : 'Fixed Amount per Winner (₹)',
            'num_winners'        : 'Number of Winners',
            'disbursement_method': 'Disbursement Method',
        }

    def clean(self):
        cleaned = super().clean()
        dist_type = cleaned.get('distribution_type')
        if dist_type == 'FIXED':
            if not cleaned.get('fixed_amount'):
                self.add_error('fixed_amount', 'Required for Fixed distribution.')
            if not cleaned.get('num_winners'):
                self.add_error('num_winners', 'Required for Fixed distribution.')
            # Validate budget is sufficient
            amt = cleaned.get('fixed_amount') or 0
            winners = cleaned.get('num_winners') or 0
            budget = cleaned.get('total_budget') or 0
            if amt and winners and (amt * winners > budget):
                raise forms.ValidationError(
                    f'Fixed amount × winners (₹{amt} × {winners} = ₹{amt*winners}) '
                    f'exceeds total budget (₹{budget}).'
                )
        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Platform Filters
# ─────────────────────────────────────────────────────────────────────────────

class Step4FiltersForm(forms.ModelForm):
    required_documents = forms.MultipleChoiceField(
        choices=DOCUMENT_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Mandatory Documents to Verify'
    )

    class Meta:
        model = Scholarship
        fields = ['min_karma', 'verification_strictness', 'essay_question']
        widgets = {
            'min_karma': forms.NumberInput(attrs={
                'type': 'range', 'min': '0', 'max': '500', 'step': '10',
                'id': 'karma_slider', 'oninput': 'karmaDisplay.innerText=this.value'
            }),
            'verification_strictness': forms.RadioSelect(),
            'essay_question': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'e.g. Why do you need this scholarship? (Leave blank to skip)'
            }),
        }
        labels = {
            'min_karma'              : 'Minimum Karma Points Required',
            'verification_strictness': 'Document Verification Strictness',
            'essay_question'         : 'Custom Essay / Question (Optional)',
        }