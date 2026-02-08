from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from scholarships.models import Scholarship
from applications.models import Application, UploadedDocument
from applications.forms import ApplicationDecisionForm

def is_organization(user):
    """Check if user has an organization profile"""
    return hasattr(user, 'organizationprofile')

@login_required
def organization_dashboard(request):
    """Dashboard for funding organizations"""
    
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')
    
    org = request.user.organizationprofile
    
    # Get organization's scholarships
    scholarships = Scholarship.objects.filter(
        organization=org.organization_name,
        is_active=True
    )
    
    # Get applications for organization's scholarships
    applications = Application.objects.filter(
        scholarship__in=scholarships
    ).select_related('student', 'scholarship').order_by('-last_action_date')
    
    # Count by status
    pending_count = applications.filter(status='PENDING').count()
    approved_count = applications.filter(status='APPROVED').count()
    
    # Calculate total disbursed (sum of award amounts for approved applications)
    total_disbursed = 0
    for app in applications.filter(status='APPROVED'):
        try:
            total_disbursed += int(app.scholarship.award_amount)
        except (ValueError, TypeError):
            pass  # Skip if award_amount is invalid
    
    context = {
        'org': org,
        'organization': org,  # For template compatibility
        'scholarships': scholarships,
        'active_scholarships': scholarships.count(),
        'total_applications': applications.count(),
        'pending_count': pending_count,
        'approved_count': approved_count,
        'total_disbursed': total_disbursed,
    }
    
    return render(request, 'funder_portal/funder_dashboard.html', context)


@login_required
def view_applications(request):
    """List all applications for organization's scholarships"""
    
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')
    
    org = request.user.organizationprofile
    
    # Get organization's scholarships
    scholarships = Scholarship.objects.filter(
        organization=org.organization_name,
        is_active=True
    )
    
    # Get applications (exclude DRAFT - only show submitted applications)
    applications = Application.objects.filter(
        scholarship__in=scholarships
    ).exclude(status='DRAFT').select_related('student', 'scholarship').order_by('-last_action_date')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Filter by scholarship
    scholarship_filter = request.GET.get('scholarship', '')
    if scholarship_filter:
        applications = applications.filter(scholarship_id=scholarship_filter)
    
    context = {
        'applications': applications,
        'scholarships': scholarships,
        'status_filter': status_filter,
        'scholarship_filter': scholarship_filter,
        'status_choices': Application.STATUS_CHOICES,
    }
    
    return render(request, 'funder_portal/applications_list.html', context)


@login_required
def application_detail(request, pk):
    """View detailed application with student info and documents"""
    
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')
    
    application = get_object_or_404(Application, pk=pk)
    org = request.user.organizationprofile
    
    # Verify this application is for this organization's scholarship
    if application.scholarship.organization != org.organization_name:
        messages.error(request, 'You do not have permission to view this application.')
        return redirect('funder_portal:view_applications')
    
    # Get uploaded documents
    documents = UploadedDocument.objects.filter(application=application)
    
    # Get student's academic records
    academic_records = application.student.academic_records.all()
    
    context = {
        'application': application,
        'student': application.student,
        'documents': documents,
        'academic_records': academic_records,
    }
    
    return render(request, 'funder_portal/application_review.html', context)


@login_required
def make_decision(request, pk):
    """Approve or reject an application"""
    
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')
    
    application = get_object_or_404(Application, pk=pk)
    org = request.user.organizationprofile
    
    # Verify this application is for this organization's scholarship
    if application.scholarship.organization != org.organization_name:
        messages.error(request, 'You do not have permission to modify this application.')
        return redirect('funder_portal:view_applications')
    
    if request.method == 'POST':
        form = ApplicationDecisionForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            notes = form.cleaned_data.get('notes', '')
            
            # Update application status
            application.status = decision
            application.save()
            
            # Update roadmap steps to reflect the decision
            from applications.models import ApplicationRoadmapStep
            
            # Mark "Under Review" as completed
            ApplicationRoadmapStep.objects.filter(
                application=application,
                step_name='Under Review'
            ).update(is_complete=True)
            
            # Mark "Organization Decision" as completed
            ApplicationRoadmapStep.objects.filter(
                application=application,
                step_name='Organization Decision'
            ).update(is_complete=True)
            
            # If approved, mark "Final Status" as completed too
            if decision == 'APPROVED':
                ApplicationRoadmapStep.objects.filter(
                    application=application,
                    step_name='Final Status'
                ).update(is_complete=True)
                
                messages.success(request, 
                    f'✅ Application approved for {application.student.full_name}!')
            else:
                # For rejection, just mark decision step as complete
                messages.success(request, 
                    f'Application rejected for {application.student.full_name}.')
            
            return redirect('funder_portal:view_applications')
    else:
        form = ApplicationDecisionForm()
    
    context = {
        'application': application,
        'form': form,
    }
    
    return render(request, 'funder_portal/make_decision.html', context)


@login_required
def manage_scholarship(request, pk=None):
    """Handles creating a new scholarship (pk=None) or editing an existing one."""
    
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')
    
    from .forms import FunderScholarshipForm
    
    organization_profile = request.user.organizationprofile
    scholarship = None
    
    if pk:  # If a primary key (pk) is passed, we are editing
        # Ensure the organization can only edit THEIR OWN scholarships
        scholarship = get_object_or_404(Scholarship, pk=pk, organization=organization_profile.organization_name)
        title = "Edit Scholarship: " + scholarship.name
    else:
        title = "Create New Scholarship"

    if request.method == 'POST':
        form = FunderScholarshipForm(request.POST, instance=scholarship)
        if form.is_valid():
            new_scholarship = form.save(commit=False)
            
            # Automatically assign organization name as string (CharField)
            new_scholarship.organization = organization_profile.organization_name
            new_scholarship.save()
            
            # Handle required documents
            from scholarships.models import RequiredDocument
            selected_docs = form.cleaned_data.get('required_documents', [])
            
            # Clear existing required documents if editing
            if pk:
                RequiredDocument.objects.filter(scholarship=new_scholarship).delete()
            
            # Create new RequiredDocument entries
            for doc_name in selected_docs:
                RequiredDocument.objects.create(
                    scholarship=new_scholarship,
                    document_name=doc_name,
                    is_mandatory=True
                )
            
            # Add success message
            if pk:
                messages.success(request, f'✅ Scholarship "{new_scholarship.name}" updated successfully!')
            else:
                messages.success(request, f'✅ Scholarship "{new_scholarship.name}" created successfully!')
            
            if selected_docs:
                messages.info(request, f'📄 {len(selected_docs)} required document(s) configured.')
            
            return redirect('funder_portal:funder_dashboard')
    else:
        form = FunderScholarshipForm(instance=scholarship)

    context = {'form': form, 'title': title, 'scholarship': scholarship}
    return render(request, 'funder_portal/manage_scholarship.html', context)


@login_required
def delete_scholarship(request, pk):
    """Delete a scholarship (organization can only delete their own)"""
    
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')
    
    organization_profile = request.user.organizationprofile
    scholarship = get_object_or_404(Scholarship, pk=pk, organization=organization_profile.organization_name)
    
    if request.method == 'POST':
        scholarship_name = scholarship.name
        scholarship.delete()
        messages.success(request, f'🗑️ Scholarship "{scholarship_name}" has been deleted successfully.')
        return redirect('funder_portal:funder_dashboard')
    
    return render(request, 'funder_portal/delete_scholarship.html', {
        'scholarship': scholarship
    })
