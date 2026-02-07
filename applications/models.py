from django.db import models
from users.models import StudentProfile, ModeratorProfile
from scholarships.models import Scholarship, RequiredDocument

class Application(models.Model):
    """Tracks a student's application for a specific scholarship."""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'), ('PENDING', 'Pending Review'), 
        ('MOD_VERIFIED', 'Moderator Verified'), ('SUBMITTED', 'Submitted to Funder'),
        ('APPROVED', 'Approved by Funder'), ('REJECTED', 'Rejected')
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    moderator_assigned = models.ForeignKey(
        ModeratorProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    
    application_link = models.URLField(max_length=2000, blank=True) # Official link if external
    last_action_date = models.DateTimeField(auto_now=True)

    class Meta:
        # Ensures a student can only apply once for the same scholarship
        unique_together = ('student', 'scholarship') 

    def __str__(self):
        return f"{self.student.full_name} - {self.scholarship.name} ({self.status})"

class UploadedDocument(models.Model):
    """Stores the files uploaded by the student."""
    
    VERIFICATION_CHOICES = [
        ('PENDING', 'Pending'), ('AI_OK', 'AI Verified OK'), 
        ('AI_FLAG', 'AI Flagged Issue'), ('MOD_OK', 'Moderator Verified OK')
    ]
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    document_type = models.ForeignKey(RequiredDocument, on_delete=models.CASCADE)
    file = models.FileField(upload_to='application_docs/') # You need to configure media settings
    
    ai_verification_status = models.CharField(max_length=10, choices=VERIFICATION_CHOICES, default='PENDING')
    moderator_verified = models.BooleanField(default=False)
    moderator_notes = models.TextField(blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.document_type.document_name} for {self.application.student.full_name}"

class ApplicationRoadmapStep(models.Model):
    """Visual progress tracker for each application."""
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    step_order = models.IntegerField()
    step_name = models.CharField(max_length=100)
    instructions = models.TextField(blank=True)
    is_complete = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['step_order']