# funder_portal/forms.py

from django import forms
from scholarships.models import Scholarship

class FunderScholarshipForm(forms.ModelForm):
    """Form for Organizations to create and edit their own scholarships."""
    
    # Common document types that students might need to upload
    DOCUMENT_CHOICES = [
        ('Aadhar Card', 'Aadhar Card / Identity Proof'),
        ('Income Certificate', 'Income Certificate / Family Income Proof'),
        ('Caste Certificate', 'Caste Certificate (SC/ST/OBC)'),
        ('Marksheet', 'Previous Year Marksheet'),
        ('Admission Letter', 'Admission Letter / Bonafide Certificate'),
        ('Bank Passbook', 'Bank Passbook / Account Details'),
        ('Photo', 'Passport Size Photo'),
        ('Disability Certificate', 'Disability Certificate (if applicable)'),
        ('Domicile Certificate', 'Domicile Certificate'),
    ]
    
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing existing scholarship, pre-populate selected documents
        if self.instance and self.instance.pk:
            from scholarships.models import RequiredDocument
            existing_docs = RequiredDocument.objects.filter(
                scholarship=self.instance
            ).values_list('document_name', flat=True)
            self.fields['required_documents'].initial = list(existing_docs)