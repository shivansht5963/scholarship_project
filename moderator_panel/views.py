# moderator_panel/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from applications.models import Application # Application model is correct here
from scholarships.models import Scholarship
from .models import TaskAssignment # <-- FIXED: TaskAssignment is in THIS app's models.py
from .forms import ScholarshipForm # <-- Don't forget this import!

# --- User Check Functions ---
def is_moderator(user):
    """Checks if the user is logged in AND is marked as a moderator."""
    return user.is_authenticated and user.is_moderator

# --- Dashboard View ---
@login_required 
@user_passes_test(is_moderator)
def moderator_dashboard(request):
    """Main dashboard showing stats and links for moderators."""
    
    # Get current statistics for the dashboard
    total_unassigned = Application.objects.filter(moderator_assigned__isnull=True).count()
    my_pending_tasks = TaskAssignment.objects.filter(
        moderator__user=request.user, 
        is_complete=False
    ).count()
    scholarships_to_verify = Scholarship.objects.filter(is_verified=False).count()
    
    context = {
        'total_unassigned_apps': total_unassigned,
        'my_pending_tasks': my_pending_tasks,
        'scholarships_to_verify': scholarships_to_verify,
    }
    
    return render(request, 'moderator_panel/moderator_dashboard.html', context)


# --- Add Scholarship View ---
@login_required
@user_passes_test(is_moderator)
def add_scholarship(request):
    """Handles the form submission for adding a new scholarship."""
    
    if request.method == 'POST':
        form = ScholarshipForm(request.POST)
        if form.is_valid():
            scholarship = form.save(commit=False)
            scholarship.is_verified = False # Default status
            scholarship.save()
            
            # Use Django's built-in success message system here later
            return redirect('moderator_dashboard') 
    else:
        form = ScholarshipForm()

    context = {'form': form, 'title': 'Add New Scholarship'}
    return render(request, 'moderator_panel/add_scholarship.html', context)