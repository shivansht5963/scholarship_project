from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from scholarships.models import Scholarship
from users.models import OrganizationProfile
from .forms import FunderScholarshipForm


def is_organization(user):
    return user.is_authenticated and user.is_organization

@login_required
@user_passes_test(is_organization)
def funder_dashboard(request):
    organization_profile = request.user.organizationprofile
    my_scholarships = Scholarship.objects.filter(organization=organization_profile).order_by('-deadline')
    
    total_schemes = my_scholarships.count()
    total_applications = 0
    
    context = {
        'organization' : organization_profile,
        'my_scholarships' : my_scholarships,
        'total_schemes' : total_schemes,
        'total_applications' : total_applications,
        
    }
    
    return render(request, 'funder_portal/funder_dashboard.html', context)

# funder_portal/views.py (continued)

# ... (is_organization and funder_dashboard above)

@login_required
@user_passes_test(is_organization)
def manage_scholarship(request, pk=None):
    """Handles creating a new scholarship (pk=None) or editing an existing one."""
    
    organization_profile = request.user.organizationprofile
    scholarship = None
    
    if pk: # If a primary key (pk) is passed, we are editing
        # Ensure the organization can only edit THEIR OWN scholarships
        scholarship = get_object_or_404(Scholarship, pk=pk, organization=organization_profile)
        title = "Edit Scholarship: " + scholarship.name
    else:
        title = "Create New Scholarship"

    if request.method == 'POST':
        form = FunderScholarshipForm(request.POST, instance=scholarship)
        if form.is_valid():
            new_scholarship = form.save(commit=False)
            
            # CRITICAL: Automatically assign the scholarship to the logged-in organization
            new_scholarship.organization = organization_profile 
            new_scholarship.funder = organization_profile.organization_name # Use their official name
            new_scholarship.save()
            
            # TODO: Add success message
            return redirect('funder_dashboard') 
    else:
        form = FunderScholarshipForm(instance=scholarship)

    context = {'form': form, 'title': title}
    return render(request, 'funder_portal/manage_scholarship.html', context)

