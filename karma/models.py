from django.db import models
from users.models import StudentProfile
from scholarships.models import Scholarship


class KarmaTransaction(models.Model):
    """Immutable audit log of all karma point changes."""
    
    TRANSACTION_TYPE_CHOICES = [
        ('FINDER_BOUNTY', 'Finder Bounty - Scholarship Submission'),
        ('OTR_COMPLETE', 'OTR Completion Bonus'),
        ('REDEEM_REWARD', 'Reward Redemption'),
        ('PENALTY_FAKE', 'Penalty - Fake Submission'),
        ('ADMIN_ADJUST', 'Admin Manual Adjustment'),
    ]
    
    student = models.ForeignKey(
        StudentProfile, 
        on_delete=models.CASCADE, 
        related_name='karma_transactions'
    )
    points = models.IntegerField(help_text="Positive for earning, negative for spending")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    description = models.TextField()
    related_scholarship = models.ForeignKey(
        Scholarship, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.full_name} - {self.points} pts ({self.get_transaction_type_display()})"


class ScholarshipSubmission(models.Model):
    """Track student-submitted scholarships for finder bounty program."""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    submitted_by = models.ForeignKey(
        StudentProfile, 
        on_delete=models.CASCADE, 
        related_name='scholarship_submissions'
    )
    scholarship_name = models.CharField(max_length=255)
    organization = models.CharField(max_length=100)
    website_url = models.URLField(max_length=2000)
    proof_document = models.FileField(
        upload_to='scholarship_submissions/%Y/%m/',
        help_text="Upload proof (screenshot, PDF, etc.)"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    karma_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, help_text="Moderator notes")
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        'users.ModeratorProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_submissions'
    )
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.scholarship_name} - {self.submitted_by.full_name} ({self.status})"


class KarmaReward(models.Model):
    """Rewards available in the perk store."""
    
    REWARD_TYPE_CHOICES = [
        ('VOUCHER', 'Voucher (Zomato, Lenskart, etc.)'),
        ('BADGE', 'Profile Badge'),
        ('PRIORITY_SERVICE', 'Priority Service'),
    ]
    
    reward_name = models.CharField(max_length=200)
    karma_cost = models.IntegerField(help_text="Points required to redeem")
    reward_type = models.CharField(max_length=20, choices=REWARD_TYPE_CHOICES)
    description = models.TextField()
    stock_quantity = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Leave blank for unlimited stock"
    )
    is_active = models.BooleanField(default=True, help_text="Active and available for redemption")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['karma_cost']
    
    def __str__(self):
        return f"{self.reward_name} ({self.karma_cost} pts)"
    
    def is_in_stock(self):
        """Check if reward is available."""
        if self.stock_quantity is None:
            return True
        return self.stock_quantity > 0


class RedemptionHistory(models.Model):
    """Track reward redemptions by students."""
    
    student = models.ForeignKey(
        StudentProfile, 
        on_delete=models.CASCADE, 
        related_name='redemptions'
    )
    reward = models.ForeignKey(
        KarmaReward, 
        on_delete=models.CASCADE,
        related_name='redemptions'
    )
    karma_spent = models.IntegerField()
    redemption_code = models.CharField(
        max_length=16, 
        unique=True,
        help_text="Unique code for reward fulfillment"
    )
    redeemed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-redeemed_at']
        verbose_name_plural = "Redemption Histories"
    
    def __str__(self):
        return f"{self.student.full_name} - {self.reward.reward_name} ({self.redemption_code})"
