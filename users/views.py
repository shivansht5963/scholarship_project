from django.shortcuts import render

# Create your views here.
# users/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import StudentProfile, OrganizationProfile
# For now, we assume if the user is not a mod or org, they are a student.

@login_required
def smart_dashboard_redirect(request):
    """
    Smart redirect based on user role.
    When user logs in or visits /dashboard, redirect them to the appropriate dashboard.
    """
    user = request.user

    # 1. Check if moderator
    if user.is_moderator:
        return redirect('moderator_dashboard')
    
    # 2. Check if organization
    elif user.is_organization:
        return redirect('funder_portal:funder_dashboard')
    
    # 3. Otherwise, assume student (default)
    else:
        return redirect('student_dashboard')  # Will create this later

@login_required
def student_dashboard(request):
    """Student dashboard - redirects to OTR if not completed"""
    try:
        profile = request.user.studentprofile

        # If OTR not completed, redirect to OTR
        if not profile.otr_completed:
            return redirect('otr_welcome')

        # OTR complete - show dashboard
        from scholarships.models import ScholarshipAward
        academic_records = profile.academic_records.all()
        documents        = profile.documents.all()
        awards           = ScholarshipAward.objects.filter(
            student=profile
        ).select_related('scholarship').order_by('-awarded_at')

        return render(request, 'users/student_dashboard.html', {
            'profile':          profile,
            'academic_records': academic_records,
            'documents':        documents,
            'awards':           awards,
            'awards_total':     sum(a.amount_awarded or 0 for a in awards),
        })

    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(
            user=request.user,
            full_name=request.user.username
        )
        return redirect('otr_welcome')
