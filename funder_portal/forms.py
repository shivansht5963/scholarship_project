# funder_portal/forms.py

from django import forms
from scholarships.models import Scholarship

class FunderScholarshipForm(forms.ModelForm):
    """Form for Organizations to create and edit their own scholarships."""
    class Meta:
        model = Scholarship
        fields = [
            'name', 
            'organization', # Even though it's their name, we include it for clarity
            'source_url', 
            'deadline', 
            'award_amount', 
            'details',
            'is_active', # Allows them to turn the scheme on/off
            # NOTE: We DO NOT include the 'organization' field here; it's set automatically in the view.
        ]
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'details': forms.Textarea(attrs={'rows': 6}),
        }