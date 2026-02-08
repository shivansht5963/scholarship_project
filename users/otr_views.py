from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import StudentProfile, AcademicRecord, StudentDocument
from .forms import OTRStep2Form, OTRStep3Form, OTRStep4Form, OTRStep5Form, OTRStep6Form

@login_required
def otr_welcome(request):
    """Step 1: OTR Welcome Page"""
    # Check if student profile exists
    try:
        profile = request.user.studentprofile
        if profile.otr_completed:
            return redirect('student_dashboard')
    except StudentProfile.DoesNotExist:
        # Create profile if doesn't exist
        profile = StudentProfile.objects.create(user=request.user, full_name=request.user.username)
    
    return render(request, 'users/otr/step1_welcome.html', {'profile': profile})

@login_required
def otr_step2(request):
    """Step 2: Basic Profile Information"""
    profile = request.user.studentprofile
    
    if request.method == 'POST':
        form = OTRStep2Form(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            profile.otr_step = 3
            profile.profile_completion = 20
            profile.save()
            messages.success(request, 'Basic information saved successfully!')
            return redirect('otr_step3')
    else:
        form = OTRStep2Form(instance=profile)
    
    return render(request, 'users/otr/step2_basic_info.html', {
        'form': form,
        'profile': profile,
        'step': 2
    })

@login_required
def otr_step3(request):
    """Step 3: Family & Category Information"""
    profile = request.user.studentprofile
    
    if request.method == 'POST':
        form = OTRStep3Form(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            profile.otr_step = 4
            profile.profile_completion = 40
            profile.save()
            messages.success(request, 'Family details saved successfully!')
            return redirect('otr_step4')
    else:
        form = OTRStep3Form(instance=profile)
    
    return render(request, 'users/otr/step3_family_info.html', {
        'form': form,
        'profile': profile,
        'step': 3
    })

@login_required
def otr_step4(request):
    """Step 4: Academic Records"""
    profile = request.user.studentprofile
    
    if request.method == 'POST':
        form = OTRStep4Form(request.POST)
        if form.is_valid():
            academic_record = form.save(commit=False)
            academic_record.student = profile
            academic_record.save()
            profile.otr_step = 5
            profile.profile_completion = 60
            profile.save()
            messages.success(request, 'Academic information saved successfully!')
            return redirect('otr_step5')
    else:
        form = OTRStep4Form()
    
    # Get existing academic records
    existing_records = profile.academic_records.all()
    
    return render(request, 'users/otr/step4_academic.html', {
        'form': form,
        'profile': profile,
        'existing_records': existing_records,
        'step': 4
    })

@login_required
def otr_step5(request):
    """Step 5: Document Upload"""
    profile = request.user.studentprofile
    
    if request.method == 'POST':
        form = OTRStep5Form(request.POST, request.FILES)
        if form.is_valid():
            # Save each uploaded document
            for doc_type, doc_file in request.FILES.items():
                StudentDocument.objects.update_or_create(
                    student=profile,
                    document_type=doc_type,
                    defaults={'file': doc_file}
                )
            profile.otr_step = 6
            profile.profile_completion = 75
            profile.save()
            messages.success(request, 'Documents uploaded successfully!')
            return redirect('otr_step6')
    else:
        form = OTRStep5Form()
    
    # Get existing documents
    existing_docs = profile.documents.all()
    
    return render(request, 'users/otr/step5_documents.html', {
        'form': form,
        'profile': profile,
        'existing_docs': existing_docs,
        'step': 5
    })

@login_required
def otr_step6(request):
    """Step 6: Banking Details"""
    profile = request.user.studentprofile
    
    if request.method == 'POST':
        form = OTRStep6Form(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            profile.otr_step = 7
            profile.profile_completion = 90
            profile.save()
            messages.success(request, 'Banking details saved successfully!')
            return redirect('otr_step7')
    else:
        form = OTRStep6Form(instance=profile)
    
    return render(request, 'users/otr/step6_banking.html', {
        'form': form,
        'profile': profile,
        'step': 6
    })

@login_required
def otr_step7(request):
    """Step 7: Review & Submit"""
    profile = request.user.studentprofile
    
    if request.method == 'POST':
        # Mark OTR as complete
        profile.otr_completed = True
        profile.profile_completion = 100
        profile.save()
        messages.success(request, '🎉 OTR completed successfully! You can now browse scholarships.')
        return redirect('student_dashboard')
    
    # Get all data for review
    academic_records = profile.academic_records.all()
    documents = profile.documents.all()
    
    return render(request, 'users/otr/step7_review.html', {
        'profile': profile,
        'academic_records': academic_records,
        'documents': documents,
        'step': 7
    })
