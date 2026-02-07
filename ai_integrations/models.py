from django.db import models
from applications.models import Application

class AICheckLog(models.Model):
    """Logs inputs and outputs of AI features for debugging and auditing."""
    
    CHECK_TYPES = [('ELIGIBILITY', 'Eligibility Check'), ('DOCUMENT_OCR', 'Document OCR/Validation')]
    
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, null=True, blank=True)
    check_type = models.CharField(max_length=50, choices=CHECK_TYPES)
    
    # Store the input data used for the check (e.g., student profile snapshot)
    input_data = models.JSONField(default=dict) 
    # Store the detailed result (e.g., match score, extracted text from OCR)
    result_json = models.JSONField(default=dict) 
    
    is_success = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_check_type_display()} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"