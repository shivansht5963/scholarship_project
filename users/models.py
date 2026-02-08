from django.db import models
from django.contrib.auth.models import AbstractUser

# --- Custom User Model ---
class User(AbstractUser):
    """Extends Django's default User for custom roles."""
    is_student = models.BooleanField(default=True)
    is_moderator = models.BooleanField(default=False)
    is_organization = models.BooleanField(default=False)
    # The default fields (username, email, password) are inherited.

    def __str__(self):
        return self.username


# --- Student Profile ---
class StudentProfile(models.Model):
    """Detailed profile for each student user."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    
    # Basic Information
    full_name = models.CharField(max_length=150)
    dob = models.DateField(null=True, blank=True, verbose_name="Date of Birth")
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], blank=True)
    
    # Family Details
    father_name = models.CharField(max_length=150, blank=True)
    mother_name = models.CharField(max_length=150, blank=True)
    annual_income = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    caste_category = models.CharField(max_length=50, choices=[
        ('General', 'General'),
        ('OBC', 'OBC'),
        ('SC', 'SC'),
        ('ST', 'ST'),
        ('EWS', 'EWS')
    ], blank=True)
    is_disabled = models.BooleanField(default=False, verbose_name="Person with Disability")
    
    # Contact & Address
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    pin_code = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    
    # Identity & Banking
    aadhaar_number = models.CharField(max_length=12, blank=True, unique=True, null=True, help_text="12-digit Aadhaar number")
    bank_account_number = models.CharField(max_length=20, blank=True)
    bank_ifsc_code = models.CharField(max_length=11, blank=True, verbose_name="IFSC Code")
    bank_name = models.CharField(max_length=100, blank=True)
    
    # OTR (One-Time Registration) Tracking
    otr_completed = models.BooleanField(default=False, help_text="Has student completed OTR?")
    otr_step = models.IntegerField(default=1, help_text="Current OTR step (1-7)")
    profile_completion = models.IntegerField(default=0, help_text="Profile completion percentage")
    
    # Karma System
    total_karma_points = models.IntegerField(default=0, help_text="Total karma points balance")
    karma_rank = models.IntegerField(null=True, blank=True, help_text="Rank on leaderboard")
    verified_scholar_badge = models.BooleanField(default=False, help_text="Has purchased verified scholar badge")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.full_name or self.user.username

# --- Academic Record (Allows multiple degrees/results) ---
class AcademicRecord(models.Model):
    """Stores academic history for a student."""
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='academic_records')
    
    degree_level = models.CharField(max_length=50, choices=[
        ('10th', '10th Grade'),
        ('12th', '12th Grade'),
        ('Diploma', 'Diploma'),
        ('UG', 'Undergraduate'),
        ('PG', 'Postgraduate'),
        ('PhD', 'Doctorate')
    ])
    stream = models.CharField(max_length=100, blank=True, help_text="E.g., Science, Commerce, Engineering")
    institution_name = models.CharField(max_length=255)
    current_year = models.IntegerField(null=True, blank=True, help_text="Current year of study")
    last_exam_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Percentage or CGPA")

    def __str__(self):
        return f"{self.student.full_name}'s {self.degree_level}"


# --- Moderator Profile ---
class ModeratorProfile(models.Model):
    """Profile for NGO representatives or teachers assisting students."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    organization_name = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=15, blank=True)
    is_verified = models.BooleanField(default=False, help_text="Verified by platform admin")
    
    def __str__(self):
        return self.organization_name
    
    
    
    
class OrganizationProfile(models.Model):
    """Details for the scholarship funding organization."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    
    organization_name = models.CharField(max_length=255, unique=True)
    contact_person = models.CharField(max_length=150)
    official_email = models.EmailField(unique=True)
    website_url = models.URLField(max_length=2000, blank=True)
    
    is_verified_funder = models.BooleanField(default=False, help_text="Verified by platform administration")
    
    def __str__(self):
        return self.organization_name


# --- Student Document Repository (OTR) ---
class StudentDocument(models.Model):
    """Repository for student documents uploaded during OTR."""
    DOCUMENT_TYPES = [
        ('aadhaar', 'Aadhaar Card'),
        ('income_cert', 'Income Certificate'),
        ('caste_cert', 'Caste Certificate'),
        ('disability_cert', 'Disability Certificate'),
        ('marksheet_10', '10th Marksheet'),
        ('marksheet_12', '12th Marksheet'),
        ('current_marksheet', 'Current Semester/Year Marksheet'),
        ('bank_passbook', 'Bank Passbook'),
        ('photo', 'Passport Photo'),
        ('other', 'Other Document'),
    ]
    
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='student_documents/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['student', 'document_type']  # One document of each type per student
    
    def __str__(self):
        return f"Document {self.id}: {self.get_document_type_display()}"