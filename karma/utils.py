"""Utility functions for karma management."""
import random
import string
from django.db import transaction, models
from django.utils import timezone
from .models import KarmaTransaction


def award_karma(student, points, transaction_type, description, related_scholarship=None):
    """
    Award karma points to a student.
    
    Args:
        student: StudentProfile instance
        points: Number of points to award (positive integer)
        transaction_type: Type from KARMA_TYPES
        description: Human-readable description
        related_scholarship: Optional Scholarship instance
    
    Returns:
        KarmaTransaction instance
    """
    from users.models import StudentProfile
    
    with transaction.atomic():
        # Update student's total karma using update() to avoid triggering signals
        StudentProfile.objects.filter(pk=student.pk).update(
            total_karma_points=models.F('total_karma_points') + points
        )
        
        # Refresh the instance to get updated value
        student.refresh_from_db()
        
        # Create transaction record
        karma_transaction = KarmaTransaction.objects.create(
            student=student,
            points=points,
            transaction_type=transaction_type,
            description=description,
            related_scholarship=related_scholarship
        )
        
        return karma_transaction


def deduct_karma(student, points, transaction_type, description, related_scholarship=None):
    """
    Deduct karma points from a student.
    
    Args:
        student: StudentProfile instance
        points: Number of points to deduct (positive integer)
        transaction_type: Type from TRANSACTION_TYPE_CHOICES
        description: Human-readable description
        related_scholarship: Optional Scholarship instance
    
    Returns:
        KarmaTransaction instance
    
    Raises:
        ValueError: If student doesn't have enough karma
    """
    from users.models import StudentProfile
    
    with transaction.atomic():
        # Update student's total karma (can go negative) using update() to avoid triggering signals
        StudentProfile.objects.filter(pk=student.pk).update(
            total_karma_points=models.F('total_karma_points') - points
        )
        
        # Refresh the instance to get updated value
        student.refresh_from_db()
        
        # Create transaction record with negative points
        karma_transaction = KarmaTransaction.objects.create(
            student=student,
            points=-points,  # Negative for deduction
            transaction_type=transaction_type,
            description=description,
            related_scholarship=related_scholarship
        )
        
        return karma_transaction


def generate_redemption_code():
    """
    Generate a unique 16-character alphanumeric redemption code.
    
    Returns:
        str: Unique redemption code (format: XXXX-XXXX-XXXX-XXXX)
    """
    from .models import RedemptionHistory
    
    while True:
        # Generate 16 random characters
        code_parts = []
        for _ in range(4):
            part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            code_parts.append(part)
        
        code = '-'.join(code_parts)
        
        # Check if code already exists
        if not RedemptionHistory.objects.filter(redemption_code=code).exists():
            return code


def update_karma_ranks():
    """
    Update karma_rank for all students based on total_karma_points.
    This should be run periodically (daily/weekly) via a cron job or management command.
    
    Students are ranked from 1 (highest karma) to N (lowest karma).
    Students with equal karma get the same rank.
    """
    from users.models import StudentProfile
    
    # Get all students ordered by karma points (descending)
    students = StudentProfile.objects.all().order_by('-total_karma_points', 'user_id')
    
    current_rank = 1
    previous_karma = None
    rank_increment = 0
    
    for student in students:
        if previous_karma is not None and student.total_karma_points < previous_karma:
            # Karma changed, update rank
            current_rank += rank_increment
            rank_increment = 1
        else:
            # Same karma as previous student, same rank
            rank_increment += 1
        
        student.karma_rank = current_rank
        previous_karma = student.total_karma_points
    
    # Bulk update for efficiency
    StudentProfile.objects.bulk_update(students, ['karma_rank'])
    
    return len(students)


def can_apply_for_scholarship(student, scholarship):
    """
    Check if a student can apply for a scholarship based on karma restrictions.
    
    Args:
        student: StudentProfile instance
        scholarship: Scholarship instance
    
    Returns:
        tuple: (bool, str) - (can_apply, reason_if_not)
    """
    # Check if scholarship has premium restriction (to be implemented later)
    # For now, no restrictions
    if student.total_karma_points < 0:
        # Check if scholarship is premium/high-value
        # This will be implemented when is_premium field is added
        return (True, "")  # No restrictions for now
    
    return (True, "")
