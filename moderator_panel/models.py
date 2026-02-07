from django.db import models
from users.models import ModeratorProfile
from applications.models import Application

class ModeratorActivityLog(models.Model):
    """Tracks all critical actions performed by moderators."""
    
    ACTION_CHOICES = [
        ('VERIFY_DOC', 'Verify Document'), ('CHANGE_STATUS', 'Change Application Status'), 
        ('NOTE_ADD', 'Add Note'), ('ASSIGN_APP', 'Assign Application')
    ]
    
    moderator = models.ForeignKey(ModeratorProfile, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES)
    
    target_application = models.ForeignKey(
        Application, on_delete=models.SET_NULL, null=True, blank=True
    )
    details = models.TextField() # Description of the action

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.moderator.user.username} - {self.get_action_type_display()}"


class TaskAssignment(models.Model):
    """Manages explicit assignments for application review."""
    
    moderator = models.ForeignKey(ModeratorProfile, on_delete=models.CASCADE)
    # OneToOne ensures an application is only assigned to one moderator at a time
    application = models.OneToOneField(Application, on_delete=models.CASCADE) 
    
    assignment_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True) # Internal review deadline
    is_complete = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Task for {self.application.student.full_name} assigned to {self.moderator.user.username}"