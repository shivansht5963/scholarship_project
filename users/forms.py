from django import forms
from .models import StudentProfile, AcademicRecord, StudentDocument

class OTRStep2Form(forms.ModelForm):
    """Step 2: Basic Profile Information"""
    class Meta:
        model = StudentProfile
        fields = ['full_name', 'dob', 'gender', 'phone', 'father_name', 'mother_name', 
                  'address', 'city', 'state', 'pin_code']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class OTRStep3Form(forms.ModelForm):
    """Step 3: Family & Category Information"""
    class Meta:
        model = StudentProfile
        fields = ['annual_income', 'caste_category', 'is_disabled']

class OTRStep4Form(forms.ModelForm):
    """Step 4: Academic Records"""
    class Meta:
        model = AcademicRecord
        fields = ['degree_level', 'stream', 'institution_name', 'current_year', 'last_exam_score']

class OTRStep5Form(forms.Form):
    """Step 5: Document Upload"""
    aadhaar = forms.FileField(required=False, label="Aadhaar Card")
    income_cert = forms.FileField(required=False, label="Income Certificate")
    caste_cert = forms.FileField(required=False, label="Caste Certificate")
    disability_cert = forms.FileField(required=False, label="Disability Certificate")
    marksheet_10 = forms.FileField(required=False, label="10th Marksheet")
    marksheet_12 = forms.FileField(required=False, label="12th Marksheet")
    current_marksheet = forms.FileField(required=False, label="Current Marksheet")
    photo = forms.FileField(required=False, label="Passport Photo")

class OTRStep6Form(forms.ModelForm):
    """Step 6: Banking Details"""
    class Meta:
        model = StudentProfile
        fields = ['aadhaar_number', 'bank_account_number', 'bank_ifsc_code', 'bank_name']
