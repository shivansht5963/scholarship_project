from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from users.models import StudentProfile
from scholarships.models import Scholarship, RequiredDocument
from .models import Application, UploadedDocument, ApplicationRoadmapStep
from .forms import DocumentUploadForm

def is_student(user):
    """Check if user has a student profile"""
    return hasattr(user, 'studentprofile')

@login_required
def create_application(request, scholarship_pk):
    """Create a new application for a scholarship"""
    
    # Verify user is a student
    if not is_student(request.user):
        messages.error(request, 'Only students can apply for scholarships.')
        return redirect('scholarships:scholarship_detail', pk=scholarship_pk)
    
    scholarship = get_object_or_404(Scholarship, pk=scholarship_pk, is_active=True)
    student = request.user.studentprofile
    
    # Check if student already applied
    existing_application = Application.objects.filter(
        student=student,
        scholarship=scholarship
    ).first()
    
    if existing_application:
        messages.info(request, f'You already have an application for {scholarship.name}.')
        return redirect('applications:application_status', pk=existing_application.pk)
    
    # Create new application
    try:
        application = Application.objects.create(
            student=student,
            scholarship=scholarship,
            status='DRAFT'
        )
        
        # Auto-populate documents from OTR if student has completed OTR
        if student.otr_completed:
            from users.models import StudentDocument
            
            # Get required documents for this scholarship
            required_docs = RequiredDocument.objects.filter(scholarship=scholarship)
            
            # Document name mapping from scholarship requirements to OTR document types
            doc_type_mapping = {
                'Aadhaar': 'aadhaar',
                'Aadhar': 'aadhaar',
                'Income': 'income_cert',
                'Caste': 'caste_cert',
                'Disability': 'disability_cert',
                '10th': 'marksheet_10',
                '12th': 'marksheet_12',
                'Marksheet': 'current_marksheet',
                'Bank': 'bank_passbook',
                'Photo': 'photo',
            }
            
            # Map OTR documents to scholarship required documents
            for req_doc in required_docs:
                # Find matching document type
                doc_type = None
                for keyword, otr_type in doc_type_mapping.items():
                    if keyword.lower() in req_doc.document_name.lower():
                        doc_type = otr_type
                        break
                
                if not doc_type:
                    continue
                
                # Get the OTR document
                otr_doc = StudentDocument.objects.filter(
                    student=student,
                    document_type=doc_type
                ).first()
                
                # If we found a matching OTR document, copy it to the application
                if otr_doc and otr_doc.file:
                    UploadedDocument.objects.create(
                        application=application,
                        document_type=req_doc,
                        file=otr_doc.file,
                        ai_verification_status='PENDING'
                    )
            
            # Check how many documents were auto-populated
            uploaded_count = UploadedDocument.objects.filter(application=application).count()
            required_count = required_docs.count()
            
            if uploaded_count == required_count and required_count > 0:
                messages.success(request, 
                    f'✅ All {uploaded_count} required documents auto-filled from your OTR! Please review and submit.')
                return redirect('applications:review_application', pk=application.pk)
            elif uploaded_count > 0:
                messages.success(request,
                    f'✅ {uploaded_count} of {required_count} documents auto-filled from your OTR. Please upload the remaining documents.')
                return redirect('applications:upload_documents', pk=application.pk)
            else:
                messages.info(request,
                    '📋 Please upload the required documents to complete your application.')
                return redirect('applications:upload_documents', pk=application.pk)
        else:
            # OTR not completed - redirect to document upload with message
            messages.warning(request,
                '⚠️ Complete your OTR profile first for automatic document population, or upload documents manually.')
            return redirect('applications:upload_documents', pk=application.pk)
    
    except IntegrityError:
        messages.error(request, 'An error occurred. You may have already applied.')
        return redirect('scholarships:scholarship_detail', pk=scholarship_pk)


@login_required
def upload_documents(request, pk):
    """Upload required documents for application"""
    
    application = get_object_or_404(Application, pk=pk)
    
    # Authorization check
    if not hasattr(request.user, 'studentprofile') or application.student != request.user.studentprofile:
        messages.error(request, 'You do not have permission to access this application.')
        return redirect('student_dashboard')
    
    # Get required documents for this scholarship
    required_docs = RequiredDocument.objects.filter(scholarship=application.scholarship)
    
    # Get already uploaded documents
    uploaded_docs = UploadedDocument.objects.filter(application=application)
    uploaded_doc_types = set(uploaded_docs.values_list('document_type_id', flat=True))
    
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.application = application
            document.save()
            
            messages.success(request, f'✅ {document.document_type.document_name} uploaded successfully!')
            return redirect('applications:upload_documents', pk=pk)
    else:
        form = DocumentUploadForm()
    
    # Filter form to only show documents not yet uploaded
    form.fields['document_type'].queryset = required_docs.exclude(id__in=uploaded_doc_types)
    
    # Check if all required documents are uploaded
    all_uploaded = required_docs.count() == uploaded_docs.count()
    
    context = {
        'application': application,
        'scholarship': application.scholarship,
        'form': form,
        'required_docs': required_docs,
        'uploaded_docs': uploaded_docs,
        'all_uploaded': all_uploaded,
    }
    
    return render(request, 'applications/upload_documents.html', context)


@login_required
def review_application(request, pk):
    """Review application before final submission"""
    
    application = get_object_or_404(Application, pk=pk)
    
    # Authorization check
    if not hasattr(request.user, 'studentprofile') or application.student != request.user.studentprofile:
        messages.error(request, 'You do not have permission to access this application.')
        return redirect('student_dashboard')
    
    # Get uploaded documents
    uploaded_docs = UploadedDocument.objects.filter(application=application)
    required_docs = RequiredDocument.objects.filter(scholarship=application.scholarship)
    
    # Check if all required docs are uploaded
    all_uploaded = required_docs.count() == uploaded_docs.count()
    
    context = {
        'application': application,
        'uploaded_docs': uploaded_docs,
        'required_docs': required_docs,
        'all_uploaded': all_uploaded,
        'student': application.student,
    }
    
    return render(request, 'applications/review.html', context)


@login_required
def submit_application(request, pk):
    """Submit application for review"""
    
    application = get_object_or_404(Application, pk=pk)
    
    # Authorization check
    if not hasattr(request.user, 'studentprofile') or application.student != request.user.studentprofile:
        messages.error(request, 'You do not have permission to access this application.')
        return redirect('student_dashboard')
    
    # Verify all required documents are uploaded
    uploaded_count = UploadedDocument.objects.filter(application=application).count()
    required_count = RequiredDocument.objects.filter(scholarship=application.scholarship).count()
    
    if uploaded_count < required_count:
        messages.error(request, 'Please upload all required documents before submitting.')
        return redirect('applications:upload_documents', pk=pk)
    
    if request.method == 'POST':
        # Update status to PENDING
        application.status = 'PENDING'
        application.save()
        
        # Create roadmap steps
        steps = [
            {'step_order': 1, 'step_name': 'Documents Uploaded', 'is_complete': True},
            {'step_order': 2, 'step_name': 'Under Review', 'is_complete': False},
            {'step_order': 3, 'step_name': 'Organization Decision', 'is_complete': False},
            {'step_order': 4, 'step_name': 'Final Status', 'is_complete': False},
        ]
        
        for step_data in steps:
            ApplicationRoadmapStep.objects.create(
                application=application,
                **step_data
            )
        
        messages.success(request, '🎉 Application submitted successfully! You will be notified when it is reviewed.')
        return redirect('applications:application_status', pk=pk)
    
    return redirect('applications:review_application', pk=pk)


@login_required
def my_applications(request):
    """List all applications for current student"""
    
    if not hasattr(request.user, 'studentprofile'):
        messages.error(request, 'Only students can view applications.')
        return redirect('student_dashboard')
    
    student = request.user.studentprofile
    applications = Application.objects.filter(student=student).order_by('-last_action_date')
    
    # Calculate status counts
    total_count = applications.count()
    pending_count = applications.filter(status='PENDING').count()
    approved_count = applications.filter(status='APPROVED').count()
    rejected_count = applications.filter(status='REJECTED').count()
    
    # Filter by status if requested
    status_filter = request.GET.get('status', '')
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    context = {
        'applications': applications,
        'status_filter': status_filter,
        'status_choices': Application.STATUS_CHOICES,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    
    return render(request, 'applications/my_applications.html', context)


@login_required
def application_status(request, pk):
    """View detailed status of a single application"""
    
    application = get_object_or_404(Application, pk=pk)
    
    # Authorization check
    if not hasattr(request.user, 'studentprofile') or application.student != request.user.studentprofile:
        messages.error(request, 'You do not have permission to access this application.')
        return redirect('student_dashboard')
    
    # Get roadmap steps
    steps = ApplicationRoadmapStep.objects.filter(application=application).order_by('step_order')
    
    # Get uploaded documents
    documents = UploadedDocument.objects.filter(application=application)
    
    context = {
        'application': application,
        'steps': steps,
        'documents': documents,
    }
    
    return render(request, 'applications/status.html', context)
