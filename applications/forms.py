from django import forms
from django.core.exceptions import ValidationError
from .models import UploadedDocument, Application

class DocumentUploadForm(forms.ModelForm):
    """Form for uploading application documents with validation"""
    
    class Meta:
        model = UploadedDocument
        fields = ['document_type', 'file']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-control',
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            })
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if not file:
            return file
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        if file.size > max_size:
            raise ValidationError('File size must be under 5MB. Please compress your file and try again.')
        
        # Validate file type
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
        file_extension = file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            raise ValidationError(
                f'Only PDF and image files (JPG, PNG) are allowed. You uploaded: .{file_extension}'
            )
        
        return file


class ApplicationDecisionForm(forms.Form):
    """Form for organizations to approve or reject applications"""
    
    DECISION_CHOICES = [
        ('APPROVED', 'Approve Application'),
        ('REJECTED', 'Reject Application'),
    ]
    
    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Add feedback or instructions for the student...',
            'class': 'form-control'
        }),
        required=False,
        label='Feedback/Notes'
    )
