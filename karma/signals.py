"""Django signals for automatic karma award."""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from users.models import StudentProfile
from .utils import award_karma


@receiver(post_save, sender=StudentProfile)
def award_otr_completion_karma(sender, instance, created, **kwargs):
    """
    Award 50 karma points when a student completes OTR.
    Triggers when otr_completed changes from False to True.
    """
    if not created and instance.otr_completed:
        # Check if there's already an OTR completion transaction
        from .models import KarmaTransaction
        
        existing_transaction = KarmaTransaction.objects.filter(
            student=instance,
            transaction_type='OTR_COMPLETE'
        ).exists()
        
        if not existing_transaction:
            # Award one-time OTR completion bonus
            award_karma(
                student=instance,
                points=50,
                transaction_type='OTR_COMPLETE',
                description="One-Time Registration (OTR) Completion Bonus"
            )
