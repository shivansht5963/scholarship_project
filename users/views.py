from django.shortcuts import render

# Create your views here.
# users/views.py

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

# Note: You will need to create the 'student_dashboard' view in a new app later (e.g., 'core' or 'student_portal').
# For now, we assume if the user is not a mod or org, they are a student.

@login_required
def smart_dashboard_redirect(request):
    """
    Redirects the user to the appropriate dashboard based on their role flags.
    This view serves as the LOGIN_REDIRECT_URL target.
    """
    user = request.user
    
    if user.is_moderator:
        # Redirect to the URL defined in moderator_panel/urls.py
        return redirect('moderator_dashboard') 
    
    elif user.is_organization:
        # Redirect to the URL defined in funder_portal/urls.py
        return redirect('funder_dashboard')
        
    else:
        # Assumes any user not flagged as Mod or Org is a standard Student
        # The student dashboard will be defined in a future app
        return redirect('student_dashboard') # Assuming this URL will exist later