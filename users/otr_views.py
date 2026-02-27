from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import StudentProfile, AcademicRecord, StudentDocument
from .forms import OTRStep2Form, OTRStep3Form, OTRStep4Form, OTRStep5Form, OTRStep6Form
from .document_verifier import verify_document

# ─── Required documents that must be verified before step 6 ───────────────────
REQUIRED_DOCS = ['aadhaar', 'income_cert', 'marksheet_10', 'photo']


@login_required
def otr_welcome(request):
    """Step 1: OTR Welcome Page"""
    try:
        profile = request.user.studentprofile
        if profile.otr_completed:
            return redirect('student_dashboard')
    except StudentProfile.DoesNotExist:
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
    
    existing_records = profile.academic_records.all()
    
    return render(request, 'users/otr/step4_academic.html', {
        'form': form,
        'profile': profile,
        'existing_records': existing_records,
        'step': 4
    })


@login_required
def otr_step5(request):
    """Step 5: Document Upload — Saves files then triggers Gemini AI verification."""
    profile = request.user.studentprofile
    
    if request.method == 'POST':
        form = OTRStep5Form(request.POST, request.FILES)
        if form.is_valid():
            uploaded_count = 0

            # Save each uploaded document and run AI verification
            for doc_type, doc_file in request.FILES.items():
                doc_obj, created = StudentDocument.objects.update_or_create(
                    student=profile,
                    document_type=doc_type,
                    defaults={
                        'file': doc_file,
                        'is_verified': False,
                        'verification_status': 'pending',
                        'verification_result': None,
                    }
                )
                uploaded_count += 1

                # ── Run Gemini AI verification immediately ──
                student_name = profile.full_name or request.user.username
                father_name = profile.father_name or ''
                mother_name = profile.mother_name or ''
                try:
                    verify_document(doc_obj, student_name, father_name, mother_name)
                except Exception:
                    pass

            if uploaded_count == 0:
                messages.warning(request, 'No files were uploaded. Please upload at least one document.')
                return redirect('otr_step5')

            profile.profile_completion = 75
            profile.save()

            messages.info(
                request,
                f'✅ {uploaded_count} document(s) uploaded and verified by AI. '
                'Check the results below before continuing.'
            )
            return redirect('otr_step5_status')
    else:
        form = OTRStep5Form()
    
    existing_docs = {doc.document_type: doc for doc in profile.documents.all()}
    
    return render(request, 'users/otr/step5_documents.html', {
        'form': form,
        'profile': profile,
        'existing_docs': existing_docs,
        'step': 5
    })


@login_required
def otr_step5_status(request):
    """
    Step 5 Status: Shows AI verification results for all uploaded documents.
    The student can only proceed to Step 6 when all REQUIRED docs are verified.
    """
    profile = request.user.studentprofile
    
    # Handle "Proceed to Step 6" button press
    if request.method == 'POST' and request.POST.get('action') == 'proceed':
        docs_by_type = {doc.document_type: doc for doc in profile.documents.all()}
        all_required_verified = all(
            docs_by_type.get(req_type) and docs_by_type[req_type].is_verified
            for req_type in REQUIRED_DOCS
        )
        if all_required_verified:
            profile.otr_step = 6
            profile.save()
            messages.success(request, '🎉 All required documents verified! Moving to banking details.')
            return redirect('otr_step6')
        else:
            messages.error(request, 'Please ensure all required documents are verified before proceeding.')

    all_docs = profile.documents.all()
    docs_by_type = {doc.document_type: doc for doc in all_docs}

    # Build a structured list with verification info for each expected document type
    doc_display_info = [
        {'type': 'aadhaar',           'label': 'Aadhaar Card',           'icon': '🆔', 'required': True},
        {'type': 'income_cert',        'label': 'Income Certificate',     'icon': '💰', 'required': True},
        {'type': 'marksheet_10',       'label': '10th Marksheet',         'icon': '📚', 'required': True},
        {'type': 'caste_cert',         'label': 'Caste Certificate',      'icon': '📄', 'required': False},
        {'type': 'disability_cert',    'label': 'Disability Certificate', 'icon': '♿', 'required': False},
        {'type': 'marksheet_12',       'label': '12th Marksheet',         'icon': '📚', 'required': False},
        {'type': 'current_marksheet',  'label': 'Current Marksheet',      'icon': '📖', 'required': False},
        {'type': 'photo',              'label': 'Passport Photo',         'icon': '📷', 'required': True},
    ]

    for item in doc_display_info:
        doc = docs_by_type.get(item['type'])
        item['doc'] = doc
        if doc:
            item['status'] = doc.verification_status
            item['result'] = doc.verification_result or {}
        else:
            item['status'] = 'not_uploaded'
            item['result'] = {}

    # Check if all required docs are verified
    all_required_verified = all(
        docs_by_type.get(req_type) and docs_by_type[req_type].is_verified
        for req_type in REQUIRED_DOCS
    )

    return render(request, 'users/otr/step5_verify_status.html', {
        'profile': profile,
        'doc_display_info': doc_display_info,
        'all_required_verified': all_required_verified,
        'required_doc_types': REQUIRED_DOCS,
        'step': 5,
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
        profile.otr_completed = True
        profile.profile_completion = 100
        profile.save()
        messages.success(request, '🎉 OTR completed successfully! You can now browse scholarships.')
        return redirect('student_dashboard')
    
    academic_records = profile.academic_records.all()
    documents = profile.documents.all()
    
    return render(request, 'users/otr/step7_review.html', {
        'profile': profile,
        'academic_records': academic_records,
        'documents': documents,
        'step': 7
    })
