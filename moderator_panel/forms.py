# moderator_panel/forms.py

from django import forms
# Import the Scholarship model from its actual location
from scholarships.models import Scholarship 

class ScholarshipForm(forms.ModelForm):
    """
    A ModelForm that automatically generates form fields
    based on the Scholarship model definition.
    """
    class Meta:
        model = Scholarship
        # Specify the fields the moderator can fill out
        fields = [
            'name', 
            'organization', 
            'source_url', 
            'deadline', 
            'award_amount', 
            'details',
            'is_active',
        ]
        # Optional: Adds HTML input type 'date' to the deadline field
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'details': forms.Textarea(attrs={'rows': 4}),
        }