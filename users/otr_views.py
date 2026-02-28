from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import StudentProfile, AcademicRecord, StudentDocument
from .forms import OTRStep2Form, OTRStep3Form, OTRStep4Form, OTRStep5Form, OTRStep6Form
from .document_verifier import verify_document
from scholarships.models import MarksheetVerification, FeesVerification

import json
import re
import time
import threading
from django.utils import timezone
import google.generativeai as genai
from django.conf import settings

GEMINI_TIMEOUT_SECONDS = 45  # Per-call timeout for step7 Gemini calls


def _otrvlog(msg: str):
    """Print a timestamped log to the terminal for OTR views."""
    ts = time.strftime('%H:%M:%S')
    print(f"[OTR_VIEW {ts}] {msg}", flush=True)

# ─── Required documents that must be verified before step 6 ───────────────────
REQUIRED_DOCS = ['aadhaar', 'marksheet_10', 'photo']


# ─── Gemini file helper ────────────────────────────────────────────────────────
def _call_gemini_for_file(file_path: str, prompt: str) -> dict:
    """Send file + prompt to Gemini, return parsed JSON dict. Empty dict on failure."""
    _otrvlog(f"  🤖 _call_gemini_for_file: {file_path}")
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        _otrvlog(f"  📂 File loaded: {len(file_bytes)} bytes")
        fname = file_path.lower()
        if fname.endswith('.pdf'):
            mime_type = 'application/pdf'
        elif fname.endswith('.png'):
            mime_type = 'image/png'
        elif fname.endswith('.webp'):
            mime_type = 'image/webp'
        else:
            mime_type = 'image/jpeg'
        _otrvlog(f"  📄 MIME: {mime_type}  — calling Gemini (timeout={GEMINI_TIMEOUT_SECONDS}s)...")
        image_part = {'mime_type': mime_type, 'data': file_bytes}

        # Thread-based timeout
        result_holder = [None]
        error_holder = [None]
        def _worker():
            try:
                result_holder[0] = model.generate_content([prompt.strip(), image_part])
            except Exception as exc:
                error_holder[0] = exc
        t = threading.Thread(target=_worker, daemon=True)
        t_start = time.time()
        t.start()
        t.join(timeout=GEMINI_TIMEOUT_SECONDS)
        elapsed = time.time() - t_start

        if t.is_alive():
            _otrvlog(f"  ⏰ TIMEOUT after {elapsed:.1f}s")
            return {'error': f'Gemini timeout after {GEMINI_TIMEOUT_SECONDS}s'}
        if error_holder[0]:
            raise error_holder[0]

        response = result_holder[0]
        _otrvlog(f"  ⚡ Gemini responded in {elapsed:.1f}s")
        raw_text = response.text.strip()
        _otrvlog(f"  📝 Response ({len(raw_text)} chars): {raw_text[:300]}{'...' if len(raw_text)>300 else ''}")
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            _otrvlog(f"  ✅ JSON parsed: {parsed}")
            return parsed
        _otrvlog(f"  ⚠️  No JSON found in response")
    except Exception as e:
        _otrvlog(f"  💥 Exception: {type(e).__name__}: {e}")
        return {'error': str(e)}
    return {}


def _names_similar(a: str, b: str) -> bool:
    """True if at least one significant word (len > 2) is common."""
    if not a or not b:
        return False
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    return bool([w for w in wa & wb if len(w) > 2])


# ─── Step 1 ──────────────────────────────────────────────────────────────────
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


# ─── Step 2 ──────────────────────────────────────────────────────────────────
@login_required
def otr_step2(request):
    """Step 2: Basic Profile Information"""
    profile = request.user.studentprofile
    if request.method == 'POST':
        form = OTRStep2Form(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            profile.otr_step = 3
            profile.profile_completion = 15
            profile.save()
            messages.success(request, 'Basic information saved successfully!')
            return redirect('otr_step3')
    else:
        form = OTRStep2Form(instance=profile)
    return render(request, 'users/otr/step2_basic_info.html', {
        'form': form, 'profile': profile, 'step': 2
    })


# ─── Step 3 ──────────────────────────────────────────────────────────────────
@login_required
def otr_step3(request):
    """Step 3: Family & Category Information"""
    profile = request.user.studentprofile
    if request.method == 'POST':
        form = OTRStep3Form(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            profile.otr_step = 4
            profile.profile_completion = 30
            profile.save()
            messages.success(request, 'Family details saved successfully!')
            return redirect('otr_step4')
    else:
        form = OTRStep3Form(instance=profile)
    return render(request, 'users/otr/step3_family_info.html', {
        'form': form, 'profile': profile, 'step': 3
    })


# ─── Step 4 ──────────────────────────────────────────────────────────────────
@login_required
def otr_step4(request):
    """Step 4: Academic Records — shows existing record if present, allows editing or adding."""
    profile = request.user.studentprofile
    existing_records = profile.academic_records.all()

    if request.method == 'POST':
        form = OTRStep4Form(request.POST)
        if form.is_valid():
            # Delete old records first so there's only ever one current record
            existing_records.delete()
            academic_record = form.save(commit=False)
            academic_record.student = profile
            academic_record.save()
            profile.otr_step = max(profile.otr_step, 5)
            profile.profile_completion = max(profile.profile_completion, 45)
            profile.save()
            messages.success(request, 'Academic information saved successfully!')
            return redirect('otr_step5')
    else:
        # Pre-fill with the latest record if it exists
        latest = existing_records.order_by('-id').first()
        form = OTRStep4Form(instance=latest) if latest else OTRStep4Form()

    return render(request, 'users/otr/step4_academic.html', {
        'form': form, 'profile': profile,
        'existing_records': existing_records, 'step': 4
    })


# ─── Step 5 ──────────────────────────────────────────────────────────────────
@login_required
def otr_step5(request):
    """Step 5: Document Upload — Saves files then triggers Gemini AI verification."""
    profile = request.user.studentprofile
    if request.method == 'POST':
        form = OTRStep5Form(request.POST, request.FILES)
        if form.is_valid():
            uploaded_count = 0
            file_items = list(request.FILES.items())
            _otrvlog(f"═══ STEP 5 POST: {len(file_items)} file(s) received for student='{profile.full_name}' (id={profile.pk})")
            for idx, (doc_type, doc_file) in enumerate(file_items, start=1):
                _otrvlog(f"  [{idx}/{len(file_items)}] Saving doc_type='{doc_type}'  filename='{doc_file.name}'  size={doc_file.size} bytes")
                doc_obj, created = StudentDocument.objects.update_or_create(
                    student=profile, document_type=doc_type,
                    defaults={
                        'file': doc_file, 'is_verified': False,
                        'verification_status': 'pending', 'verification_result': None,
                    }
                )
                _otrvlog(f"  [{idx}/{len(file_items)}] DB record {'created' if created else 'updated'}  pk={doc_obj.pk}")
                uploaded_count += 1

                _otrvlog(f"  [{idx}/{len(file_items)}] ▶ Starting Gemini verification for '{doc_type}' ...")
                t_start = time.time()
                try:
                    result = verify_document(
                        doc_obj,
                        profile.full_name or request.user.username,
                        profile.father_name or '',
                        profile.mother_name or '',
                    )
                    elapsed = time.time() - t_start
                    _otrvlog(f"  [{idx}/{len(file_items)}] ◀ Verification done in {elapsed:.1f}s  status='{result.get('verification_status')}'")
                except Exception as ex:
                    elapsed = time.time() - t_start
                    _otrvlog(f"  [{idx}/{len(file_items)}] ◀ Verification EXCEPTION in {elapsed:.1f}s: {type(ex).__name__}: {ex}")

            if uploaded_count == 0:
                _otrvlog("  ⚠️  No files uploaded — redirecting back to step5")
                messages.warning(request, 'No files were uploaded. Please upload at least one document.')
                return redirect('otr_step5')

            _otrvlog(f"═══ STEP 5 DONE: {uploaded_count} doc(s) processed → redirecting to step5_status")
            profile.profile_completion = 60
            profile.save()
            messages.info(
                request,
                f'{uploaded_count} document(s) uploaded and verified by AI. '
                'Check the results below before continuing.'
            )
            return redirect('otr_step5_status')
    else:
        form = OTRStep5Form()
    existing_docs = {doc.document_type: doc for doc in profile.documents.all()}
    return render(request, 'users/otr/step5_documents.html', {
        'form': form, 'profile': profile, 'existing_docs': existing_docs, 'step': 5
    })


# ─── Step 5 Status ───────────────────────────────────────────────────────────
@login_required
def otr_step5_status(request):
    """Step 5 Status: Shows AI verification results."""
    profile = request.user.studentprofile

    if request.method == 'POST' and request.POST.get('action') == 'proceed':
        docs_by_type = {doc.document_type: doc for doc in profile.documents.all()}
        all_required_verified = all(
            docs_by_type.get(t) and docs_by_type[t].is_verified for t in REQUIRED_DOCS
        )
        if all_required_verified:
            profile.otr_step = 6
            profile.save()
            messages.success(request, 'All required documents verified! Moving to banking details.')
            return redirect('otr_step6')
        else:
            messages.error(request, 'Please ensure all required documents are verified before proceeding.')

    all_docs = profile.documents.all()
    docs_by_type = {doc.document_type: doc for doc in all_docs}
    doc_display_info = [
        {'type': 'aadhaar',          'label': 'Aadhaar Card',           'icon': 'ID', 'required': True},
        {'type': 'income_cert',       'label': 'Income Certificate',     'icon': 'Rs', 'required': True},
        {'type': 'marksheet_10',      'label': '10th Marksheet',         'icon': 'Mk', 'required': True},
        {'type': 'caste_cert',        'label': 'Caste Certificate',      'icon': 'CA', 'required': False},
        {'type': 'disability_cert',   'label': 'Disability Certificate', 'icon': 'DI', 'required': False},
        {'type': 'marksheet_12',      'label': '12th Marksheet',         'icon': 'Mk', 'required': False},
        {'type': 'current_marksheet', 'label': 'Current Marksheet',      'icon': 'Mk', 'required': False},
        {'type': 'photo',             'label': 'Passport Photo',         'icon': 'Ph', 'required': True},
    ]
    for item in doc_display_info:
        doc = docs_by_type.get(item['type'])
        item['doc'] = doc
        item['status'] = doc.verification_status if doc else 'not_uploaded'
        item['result'] = (doc.verification_result or {}) if doc else {}

    all_required_verified = all(
        docs_by_type.get(t) and docs_by_type[t].is_verified for t in REQUIRED_DOCS
    )
    return render(request, 'users/otr/step5_verify_status.html', {
        'profile': profile,
        'doc_display_info': doc_display_info,
        'all_required_verified': all_required_verified,
        'required_doc_types': REQUIRED_DOCS,
        'step': 5,
    })


# ─── Step 6 ──────────────────────────────────────────────────────────────────
@login_required
def otr_step6(request):
    """Step 6: Banking Details"""
    profile = request.user.studentprofile
    if request.method == 'POST':
        form = OTRStep6Form(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            profile.otr_step = 7
            profile.profile_completion = 75
            profile.save()
            messages.success(request, 'Banking details saved successfully!')
            return redirect('otr_step7')
    else:
        form = OTRStep6Form(instance=profile)
    return render(request, 'users/otr/step6_banking.html', {
        'form': form, 'profile': profile, 'step': 6
    })


# ─── Step 7 (NEW) ─────────────────────────────────────────────────────────────
@login_required
def otr_step7(request):
    """
    Step 7: Academic & Financial Verification
    - Last semester marksheet  → Gemini extracts marks % + institution
    - College fees receipt     → Gemini extracts total fees + verifies college name
    """
    profile = request.user.studentprofile

    try:
        existing_marksheet = profile.marksheet_verification
    except MarksheetVerification.DoesNotExist:
        existing_marksheet = None

    try:
        existing_fees = profile.fees_verification
    except FeesVerification.DoesNotExist:
        existing_fees = None

    if request.method == 'POST':
        marksheet_file    = request.FILES.get('marksheet_file')
        fees_receipt_file = request.FILES.get('fees_receipt_file')

        _otrvlog(f"═══ STEP 7 POST: marksheet={'YES' if marksheet_file else 'NO'}  fees={'YES' if fees_receipt_file else 'NO'}  student='{profile.full_name}'")

        if not marksheet_file and not fees_receipt_file:
            _otrvlog("  ⚠️  No files received — redirecting back")
            messages.error(request, 'Please upload at least one file to continue.')
            return redirect('otr_step7')

        latest_record = profile.academic_records.order_by('-id').first()
        registered_institution = (latest_record.institution_name if latest_record else '') or ''

        # ── Marksheet processing ───────────────────────────────────────────────
        if marksheet_file:
            mv, _ = MarksheetVerification.objects.update_or_create(
                student=profile,
                defaults={'marksheet_file': marksheet_file, 'gemini_verified': False,
                          'last_sem_marks': None, 'raw_gemini_response': ''}
            )
            mv.save()

            marksheet_prompt = f"""
You are a document verification AI for an Indian scholarship platform.
Analyze this last semester marksheet image carefully.

Return ONLY a valid JSON object (no markdown, no extra text):
{{
  "student_name": "Full name of student on marksheet or null",
  "institution_name": "College or university name or null",
  "semester_or_year": "e.g. 3rd Semester or 2nd Year or null",
  "marks_percentage": numeric percentage 0-100 (convert CGPA to % as CGPA x 10) or null,
  "is_marksheet": true if this is a valid semester/year result marksheet else false,
  "rejection_reason": "reason if not valid else null"
}}"""
            _otrvlog(f"  [MARKSHEET] ▶ Calling Gemini for marksheet ...")
            t_ms = time.time()
            result = _call_gemini_for_file(mv.marksheet_file.path, marksheet_prompt)
            _otrvlog(f"  [MARKSHEET] ◀ Gemini done in {time.time()-t_ms:.1f}s  result={result}")
            mv.raw_gemini_response = json.dumps(result)
            mv.extracted_student_name = result.get('student_name') or ''
            mv.extracted_institution  = result.get('institution_name') or ''
            mv.extracted_semester     = result.get('semester_or_year') or ''
            try:
                mv.last_sem_marks = float(result['marks_percentage']) if result.get('marks_percentage') is not None else None
            except (ValueError, TypeError):
                mv.last_sem_marks = None
            is_valid = result.get('is_marksheet', False)
            name_ok  = _names_similar(mv.extracted_student_name, profile.full_name or '')
            mv.gemini_verified = bool(is_valid and (name_ok or not mv.extracted_student_name))
            mv.verified_at = timezone.now()
            mv.save()
            _otrvlog(f"  [MARKSHEET] Saved: gemini_verified={mv.gemini_verified}  marks={mv.last_sem_marks}  institution='{mv.extracted_institution}'")

        # ── Fees receipt processing ────────────────────────────────────────────
        if fees_receipt_file:
            fv, _ = FeesVerification.objects.update_or_create(
                student=profile,
                defaults={'fees_receipt_file': fees_receipt_file, 'gemini_verified': False,
                          'total_annual_fees': None, 'raw_gemini_response': ''}
            )
            fv.save()

            fees_prompt = f"""
You are a document verification AI for an Indian scholarship platform.
Analyze this college fees receipt carefully.
Student's registered college: "{registered_institution}"

Return ONLY a valid JSON object (no markdown, no extra text):
{{
  "student_name": "Student name on receipt or null",
  "college_name": "College/institution name on receipt or null",
  "total_fees_amount": integer total fees in INR or null,
  "academic_year": "e.g. 2023-24 or null",
  "is_fees_receipt": true if this is a valid college fees receipt else false,
  "college_match": true if college name on receipt matches "{registered_institution}" else false,
  "rejection_reason": "reason if not valid else null"
}}"""
            _otrvlog(f"  [FEES] ▶ Calling Gemini for fees receipt ...")
            t_fv = time.time()
            result = _call_gemini_for_file(fv.fees_receipt_file.path, fees_prompt)
            _otrvlog(f"  [FEES] ◀ Gemini done in {time.time()-t_fv:.1f}s  result={result}")
            fv.raw_gemini_response     = json.dumps(result)
            fv.extracted_student_name  = result.get('student_name') or ''
            fv.extracted_college_name  = result.get('college_name') or ''
            fv.extracted_academic_year = result.get('academic_year') or ''
            fv.college_match           = bool(result.get('college_match', False))
            try:
                fv.total_annual_fees = int(result['total_fees_amount']) if result.get('total_fees_amount') is not None else None
            except (ValueError, TypeError):
                fv.total_annual_fees = None
            fv.gemini_verified = bool(result.get('is_fees_receipt', False))
            fv.verified_at = timezone.now()
            fv.save()
            _otrvlog(f"  [FEES] Saved: gemini_verified={fv.gemini_verified}  fees={fv.total_annual_fees}  college='{fv.extracted_college_name}'")

        profile.otr_step = 8
        profile.profile_completion = 90
        profile.save()
        messages.success(request, 'Documents uploaded and AI-verified. Review your profile before final submission.')
        return redirect('otr_step8')

    return render(request, 'users/otr/step7_academic_financial.html', {
        'profile': profile,
        'existing_marksheet': existing_marksheet,
        'existing_fees': existing_fees,
        'step': 7,
    })


# ─── Step 8 (was Step 7: Review & Submit) ────────────────────────────────────
@login_required
def otr_step8(request):
    """Step 8: Review & Submit — Final confirmation, marks OTR complete."""
    profile = request.user.studentprofile

    if request.method == 'POST':
        profile.otr_completed = True
        profile.profile_completion = 100
        profile.save()
        messages.success(request, 'OTR completed successfully! You can now browse scholarships.')
        return redirect('student_dashboard')

    academic_records = profile.academic_records.all()
    documents = profile.documents.all()

    try:
        marksheet_ver = profile.marksheet_verification
    except MarksheetVerification.DoesNotExist:
        marksheet_ver = None

    try:
        fees_ver = profile.fees_verification
    except FeesVerification.DoesNotExist:
        fees_ver = None

    return render(request, 'users/otr/step8_review.html', {
        'profile': profile,
        'academic_records': academic_records,
        'documents': documents,
        'marksheet_ver': marksheet_ver,
        'fees_ver': fees_ver,
        'step': 8,
    })
