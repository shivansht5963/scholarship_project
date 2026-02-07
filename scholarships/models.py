from django.db import models
from django.contrib.postgres.fields import JSONField # Note: Use TextField if you aren't using Postgres!

class Scholarship(models.Model):
    """Master list of all aggregated scholarships."""
    
    name = models.CharField(max_length=255, unique=True)
    organization = models.CharField(max_length=100)
    source_url = models.URLField(max_length=2000)
    deadline = models.DateField()
    
    award_amount = models.CharField(max_length=50) # e.g., "50,000 INR" or "Tuition Fees"
    details = models.TextField()
    
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class EligibilityCriteria(models.Model):
    """Standardized rules for the AI matching engine."""
    
    # Simple choices for comparison operators
    OPERATOR_CHOICES = [('GT', '>'), ('LT', '<'), ('EQ', '='), ('IN', 'IN')]

    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE)
    criterion_type = models.CharField(max_length=50) # e.g., 'MIN_INCOME', 'MAX_AGE', 'MIN_GPA'
    comparison_operator = models.CharField(max_length=2, choices=OPERATOR_CHOICES, default='GT')
    value = models.CharField(max_length=255) # The value to check against (e.g., '250000', '25', '70')
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.scholarship.name}: {self.criterion_type} {self.comparison_operator} {self.value}"

class RequiredDocument(models.Model):
    """Checklist of documents needed for the scholarship."""
    
    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE)
    document_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)
    
    def __str__(self):
        return self.document_name