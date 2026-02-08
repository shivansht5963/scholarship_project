"""Views for karma system."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from users.models import StudentProfile
from scholarships.models import Scholarship
from .models import KarmaTransaction, ScholarshipSubmission, KarmaReward, RedemptionHistory
from .forms import ScholarshipSubmissionForm, SubmissionVerificationForm
from .utils import award_karma, deduct_karma, generate_redemption_code


# --- Helper Functions ---

def is_student(user):
    """Check if user is a student."""
    return user.is_authenticated and user.is_student


def is_moderator(user):
    """Check if user is a moderator."""
    return user.is_authenticated and user.is_moderator


# --- Student Views ---

@login_required
@user_passes_test(is_student)
def karma_dashboard(request):
    """Display student's karma dashboard with balance, rank, and activity feed."""
    try:
        student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('user_dashboard')
    
    # Get recent transactions
    transactions = KarmaTransaction.objects.filter(student=student)[:20]
    
    # Calculate stats
    total_earned = sum(t.points for t in KarmaTransaction.objects.filter(
        student=student, points__gt=0
    ))
    total_spent = abs(sum(t.points for t in KarmaTransaction.objects.filter(
        student=student, points__lt=0
    )))
    
    context = {
        'student': student,
        'total_karma': student.total_karma_points,
        'karma_rank': student.karma_rank or 'Unranked',
        'total_earned': total_earned,
        'total_spent': total_spent,
        'transactions': transactions,
        'verified_badge': student.verified_scholar_badge,
    }
    
    return render(request, 'karma/karma_dashboard.html', context)


@login_required
@user_passes_test(is_student)
def submit_scholarship(request):
    """Form for students to submit new scholarships for finder bounty."""
    try:
        student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        form = ScholarshipSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.submitted_by = student
            submission.save()
            
            messages.success(
                request,
                'Scholarship submitted successfully! You will earn 100 karma points once approved by moderators.'
            )
            return redirect('karma:karma_dashboard')
    else:
        form = ScholarshipSubmissionForm()
    
    # Get user's previous submissions
    previous_submissions = ScholarshipSubmission.objects.filter(
        submitted_by=student
    ).order_by('-submitted_at')[:5]
    
    context = {
        'form': form,
        'previous_submissions': previous_submissions,
    }
    
    return render(request, 'karma/submit_scholarship.html', context)


@login_required
@user_passes_test(is_student)
def karma_leaderboard(request):
    """Display karma leaderboard with top students."""
    # Get all students with karma, ordered by points
    students = StudentProfile.objects.filter(
        total_karma_points__gt=0
    ).order_by('-total_karma_points', 'user_id')
    
    # Paginate - 50 per page
    paginator = Paginator(students, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get current student
    try:
        current_student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        current_student = None
    
    context = {
        'page_obj': page_obj,
        'current_student': current_student,
    }
    
    return render(request, 'karma/leaderboard.html', context)


@login_required
@user_passes_test(is_student)
def karma_store(request):
    """Display available rewards in the perk store."""
    try:
        student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('user_dashboard')
    
    # Get active rewards
    rewards = KarmaReward.objects.filter(is_active=True).order_by('karma_cost')
    
    # Filter by type if specified
    reward_type = request.GET.get('type')
    if reward_type:
        rewards = rewards.filter(reward_type=reward_type)
    
    context = {
        'rewards': rewards,
        'student_karma': student.total_karma_points,
        'filter_type': reward_type,
    }
    
    return render(request, 'karma/store.html', context)


@login_required
@user_passes_test(is_student)
def redeem_reward(request, reward_id):
    """Process reward redemption."""
    try:
        student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('user_dashboard')
    
    reward = get_object_or_404(KarmaReward, id=reward_id, is_active=True)
    
    # Check if student has enough karma
    if student.total_karma_points < reward.karma_cost:
        messages.error(
            request,
            f'Insufficient karma! You need {reward.karma_cost} points but only have {student.total_karma_points} points.'
        )
        return redirect('karma:karma_store')
    
    # Check stock
    if not reward.is_in_stock():
        messages.error(request, 'This reward is currently out of stock.')
        return redirect('karma:karma_store')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Generate redemption code
                code = generate_redemption_code()
                
                # Deduct karma
                deduct_karma(
                    student=student,
                    points=reward.karma_cost,
                    transaction_type='REDEEM_REWARD',
                    description=f'Redeemed: {reward.reward_name}'
                )
                
                # Create redemption record
                redemption = RedemptionHistory.objects.create(
                    student=student,
                    reward=reward,
                    karma_spent=reward.karma_cost,
                    redemption_code=code
                )
                
                # Decrement stock if not unlimited
                if reward.stock_quantity is not None:
                    reward.stock_quantity -= 1
                    reward.save(update_fields=['stock_quantity'])
                
                # For badge purchases, update student profile
                if reward.reward_type == 'BADGE' and 'Verified Scholar' in reward.reward_name:
                    student.verified_scholar_badge = True
                    student.save(update_fields=['verified_scholar_badge'])
                
                messages.success(request, 'Reward redeemed successfully!')
                return render(request, 'karma/redeem_success.html', {
                    'redemption': redemption,
                    'reward': reward,
                })
        
        except Exception as e:
            messages.error(request, f'Error redeeming reward: {str(e)}')
            return redirect('karma:karma_store')
    
    # GET request - show confirmation page
    context = {
        'reward': reward,
        'student_karma': student.total_karma_points,
    }
    
    return render(request, 'karma/redeem_confirm.html', context)


# --- Moderator Views ---

@login_required
@user_passes_test(is_moderator)
def moderator_karma_overview(request):
    """Display pending scholarship submissions for moderator review."""
    pending_submissions = ScholarshipSubmission.objects.filter(
        status='PENDING'
    ).order_by('-submitted_at')
    
    # Paginate
    paginator = Paginator(pending_submissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_pending': pending_submissions.count(),
    }
    
    return render(request, 'karma/moderator/overview.html', context)


@login_required
@user_passes_test(is_moderator)
def verify_submission(request, submission_id):
    """Approve or reject a scholarship submission."""
    submission = get_object_or_404(ScholarshipSubmission, id=submission_id)
    
    if request.method == 'POST':
        form = SubmissionVerificationForm(request.POST, instance=submission)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.reviewed_at = timezone.now()
            submission.reviewed_by = request.user.moderatorprofile
            
            if submission.status == 'APPROVED':
                # Award 100 karma points
                try:
                    with transaction.atomic():
                        # Create scholarship entry
                        scholarship = Scholarship.objects.create(
                            name=submission.scholarship_name,
                            organization=submission.organization,
                            source_url=submission.website_url,
                            deadline=timezone.now().date() + timedelta(days=30),  # Placeholder
                            award_amount="To be updated",
                            details="Found by student. Details to be added by moderator.",
                            found_by_student=submission.submitted_by,
                            finder_karma_awarded=100
                        )
                        
                        # Award karma
                        award_karma(
                            student=submission.submitted_by,
                            points=100,
                            transaction_type='FINDER_BOUNTY',
                            description=f'Finder bounty for submitting: {submission.scholarship_name}',
                            related_scholarship=scholarship
                        )
                        
                        submission.karma_awarded = 100
                        submission.save()
                        
                        messages.success(request, f'Submission approved! 100 karma points awarded to {submission.submitted_by.full_name}.')
                except Exception as e:
                    messages.error(request, f'Error processing approval: {str(e)}')
                    return redirect('karma:moderator_overview')
            
            elif submission.status == 'REJECTED':
                # Apply penalty
                try:
                    deduct_karma(
                        student=submission.submitted_by,
                        points=100,
                        transaction_type='PENALTY_FAKE',
                        description=f'Penalty for fake submission: {submission.scholarship_name}'
                    )
                    submission.karma_awarded = -100
                    submission.save()
                    messages.warning(request, f'Submission rejected. -100 karma penalty applied to {submission.submitted_by.full_name}.')
                except Exception as e:
                    submission.save() # Save status even if penalty fails
                    messages.error(request, f'Submission rejected but error applying penalty: {str(e)}')
            
            return redirect('karma:moderator_overview')
    else:
        form = SubmissionVerificationForm(instance=submission)
    
    context = {
        'submission': submission,
        'form': form,
    }
    
    return render(request, 'karma/moderator/verify_submission.html', context)
