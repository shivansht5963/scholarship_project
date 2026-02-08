"""Forms for karma system."""
from django import forms
from .models import ScholarshipSubmission


class ScholarshipSubmissionForm(forms.ModelForm):
    """Form for students to submit new scholarships for finder bounty."""
    
    class Meta:
        model = ScholarshipSubmission
        fields = ['scholarship_name', 'organization', 'website_url', 'proof_document']
        widgets = {
            'scholarship_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter scholarship name',
                'required': True
            }),
            'organization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter organization name',
                'required': True
            }),
            'website_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/scholarship',
                'required': True
            }),
            'proof_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
                'required': True
            })
        }
        help_texts = {
            'scholarship_name': 'Official name of the scholarship',
            'organization': 'Organization/company offering the scholarship',
            'website_url': 'Direct link to the scholarship page',
            'proof_document': 'Upload screenshot or PDF as proof (max 10MB)'
        }
    
    def clean_proof_document(self):
        """Validate file upload."""
        file = self.cleaned_data.get('proof_document')
        if file:
            # Check file size (10MB max)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 10MB")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            file_ext = file.name.lower()[file.name.rfind('.'):]
            if file_ext not in allowed_extensions:
                raise forms.ValidationError(
                    "Only PDF and image files are allowed (PDF, JPG, PNG)"
                )
        return file


class SubmissionVerificationForm(forms.ModelForm):
    """Form for moderators to approve/reject scholarship submissions."""
    
    class Meta:
        model = ScholarshipSubmission
        fields = ['status', 'admin_notes']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'admin_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Add any notes about this submission...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit status choices to APPROVED and REJECTED only
        self.fields['status'].choices = [
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
        ]
