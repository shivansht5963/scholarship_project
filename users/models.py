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
    """Detailed profile information for scholarship matching."""
    
    # Choices for core profile fields
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    CASTE_CHOICES = [('GEN', 'General'), ('OBC', 'OBC'), ('SC', 'SC'), ('ST', 'ST')]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    
    full_name = models.CharField(max_length=255)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    
    caste_category = models.CharField(max_length=5, choices=CASTE_CHOICES, default='GEN')
    annual_income = models.IntegerField(default=0, help_text="Family annual income in Rupees")
    is_disabled = models.BooleanField(default=False)
    
    address = models.TextField(blank=True)
    pin_code = models.CharField(max_length=10, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.full_name}"

# --- Academic Record (Allows multiple degrees/results) ---
class AcademicRecord(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    degree_level = models.CharField(max_length=50) # e.g., Diploma, ITI
    stream = models.CharField(max_length=100) # e.g., Mechanical, CSE
    institution_name = models.CharField(max_length=255)
    current_year = models.IntegerField(default=1) # 1, 2, 3...
    last_exam_score = models.FloatField(null=True, blank=True, help_text="Percentage or CGPA")

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