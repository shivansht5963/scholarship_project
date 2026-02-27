# moderator_panel/forms.py

from django import forms
from scholarships.models import Scholarship


class ScholarshipForm(forms.ModelForm):
    """
    Legacy moderator form for manually adding/verifying aggregated scholarships.
    Uses the legacy fields (source_url, award_amount, details) that are kept
    as nullable on the new Scholarship model for backward compatibility.
    """
    class Meta:
        model = Scholarship
        # Using legacy fields that still exist on the model (now nullable)
        fields = [
            'title',        # was 'name' — renamed to 'title' in new model
            'organization', # still exists as a legacy CharField
            'source_url',
            'deadline',
            'award_amount',
            'details',
            'is_active',
        ]
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'details':  forms.Textarea(attrs={'rows': 4}),
        }