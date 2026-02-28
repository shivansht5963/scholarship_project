# funder_portal/views.py

import json
import hmac
import hashlib

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone

from scholarships.models import Scholarship, ScholarshipFunding, RequiredDocument
from applications.models import Application, UploadedDocument
from applications.forms import ApplicationDecisionForm


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def is_organization(user):
    return hasattr(user, 'organizationprofile')


def org_required(view_func):
    """Decorator: redirect non-org users away."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not is_organization(request.user):
            messages.error(request, 'Access denied. Organizations only.')
            return redirect('student_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def organization_dashboard(request):
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')

    org = request.user.organizationprofile

    # Scholarships belonging to this org via FK
    scholarships = Scholarship.objects.filter(org_profile=org).order_by('-created_at')

    # Also catch legacy ones linked by org name string
    legacy_scholarships = Scholarship.objects.filter(
        organization=org.organization_name, org_profile__isnull=True
    )
    all_scholarships = list(scholarships) + list(legacy_scholarships)

    scholarship_ids = [s.pk for s in all_scholarships]
    applications = Application.objects.filter(
        scholarship_id__in=scholarship_ids
    ).select_related('student', 'scholarship').order_by('-last_action_date')

    pending_count  = applications.filter(status='PENDING').count()
    approved_count = applications.filter(status='APPROVED').count()

    total_disbursed = 0
    for app in applications.filter(status='APPROVED'):
        try:
            total_disbursed += int(app.scholarship.total_budget or 0)
        except (ValueError, TypeError):
            pass

    # Drafts (unpaid scholarships)
    draft_scholarships = scholarships.filter(is_active=False, is_funded=False)

    # Total escrow = sum of PAID ScholarshipFunding records for this org's scholarships
    from scholarships.models import ScholarshipFunding
    from django.db.models import Sum
    total_escrow = ScholarshipFunding.objects.filter(
        scholarship_id__in=scholarship_ids,
        status='PAID'
    ).aggregate(s=Sum('amount_paise'))['s'] or 0
    total_escrow = total_escrow // 100  # paise → rupees

    context = {
        'org':                 org,
        'organization':        org,
        'scholarships':        scholarships,
        'draft_scholarships':  draft_scholarships,
        'active_scholarships': scholarships.filter(is_active=True).count(),
        'total_applications':  applications.count(),
        'pending_count':       pending_count,
        'approved_count':      approved_count,
        'total_disbursed':     total_disbursed,
        'total_escrow':        total_escrow,
    }
    return render(request, 'funder_portal/funder_dashboard.html', context)



# ─────────────────────────────────────────────────────────────────────────────
# MULTI‑STEP SCHOLARSHIP CREATION WIZARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def create_step1(request):
    """Step 1 — The Basics"""
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')

    from .forms import Step1BasicsForm

    if request.method == 'POST':
        form = Step1BasicsForm(request.POST, request.FILES)
        if form.is_valid():
            scholarship = form.save(commit=False)
            scholarship.org_profile  = request.user.organizationprofile
            scholarship.organization = request.user.organizationprofile.organization_name
            scholarship.is_active    = False
            scholarship.is_funded    = False
            scholarship.save()
            messages.success(request, '✅ Step 1 saved!')
            return redirect('funder_portal:create_step2', draft_id=scholarship.pk)
    else:
        form = Step1BasicsForm()

    return render(request, 'funder_portal/create_step1.html', {
        'form': form, 'step': 1, 'total_steps': 4,
        'step_title': 'The Basics',
    })


@login_required
def create_step2(request, draft_id):
    """Step 2 — Eligibility Criteria"""
    if not is_organization(request.user):
        messages.error(request, 'Access denied.')
        return redirect('student_dashboard')

    from .forms import Step2EligibilityForm

    scholarship = get_object_or_404(
        Scholarship, pk=draft_id, org_profile=request.user.organizationprofile
    )

    if request.method == 'POST':
        form = Step2EligibilityForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            scholarship.education_level    = cd['education_level']
            scholarship.max_family_income  = cd.get('max_family_income')
            scholarship.min_percentage     = cd.get('min_percentage')

            # Parse comma-separated courses into JSON list
            raw_courses = cd.get('courses_raw', '').strip()
            courses_list = [c.strip() for c in raw_courses.split(',') if c.strip()] if raw_courses else []
            scholarship.set_courses(courses_list)

            # Demographic focus list → JSON
            scholarship.set_demographic_focus(cd.get('demographic_focus', []))
            scholarship.save()

            messages.success(request, '✅ Step 2 saved!')
            return redirect('funder_portal:create_step3', draft_id=scholarship.pk)
    else:
        # Pre-populate from existing data
        initial = {
            'education_level':   scholarship.education_level,
            'max_family_income': scholarship.max_family_income,
            'min_percentage':    scholarship.min_percentage,
            'courses_raw':       ', '.join(scholarship.get_courses()),
            'demographic_focus': scholarship.get_demographic_focus(),
        }
        form = Step2EligibilityForm(initial=initial)

    return render(request, 'funder_portal/create_step2.html', {
        'form': form, 'step': 2, 'total_steps': 4,
        'scholarship': scholarship,
        'step_title': 'Eligibility Criteria',
    })


@login_required
def create_step3(request, draft_id):
    """Step 3 — Financials & Distribution"""
    if not is_organization(request.user):
        messages.error(request, 'Access denied.')
        return redirect('student_dashboard')

    from .forms import Step3FinancialsForm

    scholarship = get_object_or_404(
        Scholarship, pk=draft_id, org_profile=request.user.organizationprofile
    )

    if request.method == 'POST':
        form = Step3FinancialsForm(request.POST, instance=scholarship)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Step 3 saved!')
            return redirect('funder_portal:create_step4', draft_id=scholarship.pk)
    else:
        form = Step3FinancialsForm(instance=scholarship)

    return render(request, 'funder_portal/create_step3.html', {
        'form': form, 'step': 3, 'total_steps': 4,
        'scholarship': scholarship,
        'step_title': 'Financials & Distribution',
    })


@login_required
def create_step4(request, draft_id):
    """Step 4 — Platform Filters + Review (before payment)"""
    if not is_organization(request.user):
        messages.error(request, 'Access denied.')
        return redirect('student_dashboard')

    from .forms import Step4FiltersForm

    scholarship = get_object_or_404(
        Scholarship, pk=draft_id, org_profile=request.user.organizationprofile
    )

    if request.method == 'POST':
        form = Step4FiltersForm(request.POST, instance=scholarship)
        if form.is_valid():
            s = form.save()

            # Handle required documents
            selected_docs = form.cleaned_data.get('required_documents', [])
            RequiredDocument.objects.filter(scholarship=s).delete()
            for doc_name in selected_docs:
                RequiredDocument.objects.create(
                    scholarship=s,
                    document_name=doc_name,
                    is_mandatory=True,
                    verification_strictness=s.verification_strictness,
                )

            messages.success(request, '✅ Step 4 saved! Now review and pay to publish.')
            return redirect('funder_portal:scholarship_review', draft_id=scholarship.pk)
    else:
        existing_docs = list(
            RequiredDocument.objects.filter(scholarship=scholarship).values_list('document_name', flat=True)
        )
        form = Step4FiltersForm(instance=scholarship, initial={'required_documents': existing_docs})

    return render(request, 'funder_portal/create_step4.html', {
        'form': form, 'step': 4, 'total_steps': 4,
        'scholarship': scholarship,
        'step_title': 'Platform Filters',
    })


@login_required
def scholarship_review(request, draft_id):
    """Read-only summary page before Razorpay payment."""
    if not is_organization(request.user):
        messages.error(request, 'Access denied.')
        return redirect('student_dashboard')

    scholarship = get_object_or_404(
        Scholarship, pk=draft_id, org_profile=request.user.organizationprofile
    )
    required_docs = RequiredDocument.objects.filter(scholarship=scholarship)

    # Check if already paid
    funding = ScholarshipFunding.objects.filter(scholarship=scholarship).first()
    is_paid = (funding is not None and funding.status == 'PAID')

    context = {
        'scholarship': scholarship,
        'required_docs': required_docs,
        'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_placeholder'),
        'courses': scholarship.get_courses(),
        'demographics': scholarship.get_demographic_focus(),
        'is_paid': is_paid,
    }
    return render(request, 'funder_portal/scholarship_review.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# RAZORPAY — INITIATE PAYMENT
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def initiate_payment(request, draft_id):
    """Creates a Razorpay Order and returns order details as JSON."""
    if not is_organization(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    scholarship = get_object_or_404(
        Scholarship, pk=draft_id, org_profile=request.user.organizationprofile
    )

    if scholarship.is_funded:
        return JsonResponse({'error': 'Already paid'}, status=400)

    if not scholarship.total_budget:
        return JsonResponse({'error': 'Total budget not set'}, status=400)

    amount_paise = scholarship.total_budget * 100  # INR → paise

    try:
        import razorpay
        client = razorpay.Client(auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET,
        ))
        order_data = {
            'amount':   amount_paise,
            'currency': 'INR',
            'receipt':  f'sch_{scholarship.pk}',
        }
        order = client.order.create(order_data)
        # Upsert the funding ledger record
        funding, _ = ScholarshipFunding.objects.get_or_create(scholarship=scholarship)
        funding.razorpay_order_id = order['id']
        funding.amount_paise      = amount_paise
        funding.status            = 'PENDING'
        funding.save()

        return JsonResponse({
            'order_id': order['id'],
            'amount':   amount_paise,
            'currency': 'INR',
            'key':      settings.RAZORPAY_KEY_ID,
            'name':     scholarship.title,
            'org_name': request.user.organizationprofile.organization_name,
        })
    except ImportError:
        # razorpay not installed — demo mode
        funding, _ = ScholarshipFunding.objects.get_or_create(scholarship=scholarship)
        funding.amount_paise = amount_paise
        funding.status       = 'PENDING'
        funding.save()
        return JsonResponse({
            'order_id': f'order_DEMO_{scholarship.pk}',
            'amount':   amount_paise,
            'currency': 'INR',
            'key':      'rzp_test_demo',
            'name':     scholarship.title,
            'org_name': request.user.organizationprofile.organization_name,
            'demo_mode': True,
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())          # log full trace to server console
        return JsonResponse({'error': str(e)}, status=500)



# ─────────────────────────────────────────────────────────────────────────────
# RAZORPAY — PAYMENT CALLBACK
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def payment_callback(request):
    """
    Called after Razorpay checkout completes (via AJAX from template).
    Verifies signature, marks scholarship as funded & active.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = json.loads(request.body)
    order_id   = data.get('razorpay_order_id', '')
    payment_id = data.get('razorpay_payment_id', '')
    signature  = data.get('razorpay_signature', '')
    demo_mode  = data.get('demo_mode', False)

    try:
        funding = ScholarshipFunding.objects.get(razorpay_order_id=order_id)
    except ScholarshipFunding.DoesNotExist:
        # Demo mode: find by scholarship_id from notes
        scholarship_id = data.get('scholarship_id')
        if not scholarship_id:
            return JsonResponse({'error': 'Funding record not found'}, status=404)
        funding = get_object_or_404(ScholarshipFunding, scholarship_id=scholarship_id)

    if not demo_mode:
        # Verify Razorpay signature
        try:
            import razorpay
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                'razorpay_order_id':   order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature':  signature,
            })
        except Exception:
            return JsonResponse({'error': 'Payment verification failed'}, status=400)
    else:
        # Demo mode — accept without real verification
        payment_id = f'pay_DEMO_{funding.scholarship.pk}'
        signature  = 'DEMO_SIGNATURE'

    # Update ledger
    funding.razorpay_payment_id = payment_id
    funding.razorpay_signature  = signature
    funding.status              = 'PAID'
    funding.paid_at             = timezone.now()
    funding.save()

    # Activate scholarship
    scholarship = funding.scholarship
    scholarship.is_funded = True
    scholarship.is_active = True
    scholarship.save()

    return JsonResponse({
        'status': 'success',
        'message': f'🎉 Scholarship "{scholarship.title}" is now live!',
        'redirect_url': '/funder/dashboard/',
    })


# ─────────────────────────────────────────────────────────────────────────────
# EXISTING VIEWS (unchanged logic, updated field names)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def view_applications(request):
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')

    org = request.user.organizationprofile
    scholarships = Scholarship.objects.filter(org_profile=org)

    applications = Application.objects.filter(
        scholarship__in=scholarships
    ).exclude(status='DRAFT').select_related('student', 'scholarship').order_by('-last_action_date')

    status_filter      = request.GET.get('status', '')
    scholarship_filter = request.GET.get('scholarship', '')
    if status_filter:
        applications = applications.filter(status=status_filter)
    if scholarship_filter:
        applications = applications.filter(scholarship_id=scholarship_filter)

    return render(request, 'funder_portal/applications_list.html', {
        'applications':       applications,
        'scholarships':       scholarships,
        'status_filter':      status_filter,
        'scholarship_filter': scholarship_filter,
        'status_choices':     Application.STATUS_CHOICES,
    })


@login_required
def application_detail(request, pk):
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')

    application = get_object_or_404(Application, pk=pk)
    org = request.user.organizationprofile

    if application.scholarship.org_profile != org:
        messages.error(request, 'You do not have permission to view this application.')
        return redirect('funder_portal:view_applications')

    documents       = UploadedDocument.objects.filter(application=application)
    academic_records = application.student.academic_records.all()

    return render(request, 'funder_portal/application_review.html', {
        'application':    application,
        'student':        application.student,
        'documents':      documents,
        'academic_records': academic_records,
    })


@login_required
def make_decision(request, pk):
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')

    application = get_object_or_404(Application, pk=pk)
    org = request.user.organizationprofile

    if application.scholarship.org_profile != org:
        messages.error(request, 'You do not have permission.')
        return redirect('funder_portal:view_applications')

    if request.method == 'POST':
        form = ApplicationDecisionForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            application.status = decision
            application.save()

            from applications.models import ApplicationRoadmapStep
            ApplicationRoadmapStep.objects.filter(
                application=application, step_name='Under Review'
            ).update(is_complete=True)
            ApplicationRoadmapStep.objects.filter(
                application=application, step_name='Organization Decision'
            ).update(is_complete=True)

            if decision == 'APPROVED':
                ApplicationRoadmapStep.objects.filter(
                    application=application, step_name='Final Status'
                ).update(is_complete=True)
                messages.success(request, f'✅ Application approved for {application.student.full_name}!')
            else:
                messages.success(request, f'Application rejected for {application.student.full_name}.')

            return redirect('funder_portal:view_applications')
    else:
        form = ApplicationDecisionForm()

    return render(request, 'funder_portal/make_decision.html', {
        'application': application, 'form': form,
    })


@login_required
def manage_scholarship(request, pk=None):
    """Legacy single-page form — redirects to new wizard."""
    if pk:
        return redirect('funder_portal:create_step1')
    return redirect('funder_portal:create_step1')


@login_required
def delete_scholarship(request, pk):
    if not is_organization(request.user):
        messages.error(request, 'Access denied. Organizations only.')
        return redirect('student_dashboard')

    org = request.user.organizationprofile
    scholarship = get_object_or_404(Scholarship, pk=pk, org_profile=org)

    if request.method == 'POST':
        name = scholarship.title
        scholarship.delete()
        messages.success(request, f'🗑️ Scholarship "{name}" has been deleted.')
        return redirect('funder_portal:funder_dashboard')

    return render(request, 'funder_portal/delete_scholarship.html', {'scholarship': scholarship})


# ─────────────────────────────────────────────────────────────────────────────
# MERIT LIST  (Phase 7E)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@org_required
def merit_list_view(request, pk):
    """
    Shows the ranked merit list for a scholarship.
    Available once:
      - scholarship.deadline has passed, OR
      - org manually closes applications (applications_closed=True)

    POST with action=close   → closes applications
    """
    scholarship = get_object_or_404(
        Scholarship,
        pk=pk,
        org_profile=request.user.organizationprofile
    )

    # ── Handle manual close ───────────────────────────────────────────────────
    if request.method == 'POST' and request.POST.get('action') == 'close':
        scholarship.applications_closed = True
        scholarship.closed_at = timezone.now()
        scholarship.save(update_fields=['applications_closed', 'closed_at'])
        messages.success(request, 'Applications closed. Merit list is now visible.')
        return redirect('funder_portal:merit_list', pk=pk)

    # ── Check if merit list should be shown ───────────────────────────────────
    from scholarships.models import ScholarshipAward
    from scholarships.award_engine import get_merit_list

    now = timezone.now()
    is_closed = scholarship.applications_closed or (scholarship.deadline and scholarship.deadline < now)
    merit_list_data = []
    if is_closed:
        merit_list_data = get_merit_list(scholarship)

    # ── Count already-awarded ─────────────────────────────────────────────────
    already_awarded = ScholarshipAward.objects.filter(scholarship=scholarship).count()

    return render(request, 'funder_portal/merit_list.html', {
        'scholarship':     scholarship,
        'is_closed':       is_closed,
        'merit_list':      merit_list_data,
        'num_winners':     scholarship.num_winners or 1,
        'already_awarded': already_awarded,
        'now':             now,
    })


@login_required
@org_required
def approve_winners_view(request, pk):
    """
    POST-only view.  Approves top N applicants from the merit list and
    triggers bank transfers for BANK_TRANSFER scholarships.
    """
    scholarship = get_object_or_404(
        Scholarship,
        pk=pk,
        org_profile=request.user.organizationprofile
    )

    if request.method != 'POST':
        return redirect('funder_portal:merit_list', pk=pk)

    from scholarships.award_engine import auto_approve_winners, trigger_bank_transfer
    from scholarships.models import ScholarshipAward

    awards = auto_approve_winners(scholarship)

    if not awards:
        messages.warning(request, 'No eligible applicants found or all already awarded.')
        return redirect('funder_portal:merit_list', pk=pk)

    # Trigger bank transfers for BANK_TRANSFER scholarships
    transfer_count = 0
    if scholarship.disbursement_method == 'BANK_TRANSFER':
        for award in awards:
            payout_id = trigger_bank_transfer(award)
            if payout_id:
                transfer_count += 1

    messages.success(
        request,
        f'{len(awards)} winner(s) approved. '
        + (f'{transfer_count} bank transfer(s) initiated.' if transfer_count else
           'Manual disbursement required — check your disbursement settings.')
    )
    return redirect('funder_portal:merit_list', pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
# RAZORPAY PAYOUT WEBHOOK  (Phase 7F)
# ─────────────────────────────────────────────────────────────────────────────

import logging
_wh_logger = logging.getLogger(__name__)


@csrf_exempt
def razorpay_payout_webhook(request):
    """
    Receives Razorpay Payouts webhooks.
    Events handled:
        payout.processed  → transfer_status = DONE
        payout.failed     → transfer_status = FAILED
        payout.reversed   → transfer_status = FAILED

    Verification: HMAC-SHA256 of raw body with RAZORPAY_WEBHOOK_SECRET.
    Configure this URL in the Razorpay dashboard → Webhooks → Add New.
    """
    if request.method != 'POST':
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['POST'])

    # ── Signature verification ────────────────────────────────────────────────
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    signature      = request.headers.get('X-Razorpay-Signature', '')

    if webhook_secret and signature:
        expected = hmac.new(
            webhook_secret.encode(),
            request.body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            _wh_logger.warning("Payout webhook: invalid signature")
            return JsonResponse({'error': 'invalid signature'}, status=400)

    # ── Parse payload ─────────────────────────────────────────────────────────
    try:
        payload = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid JSON'}, status=400)

    event      = payload.get('event', '')
    payout_obj = payload.get('payload', {}).get('payout', {}).get('entity', {})
    payout_id  = payout_obj.get('id', '')
    reference  = payout_obj.get('reference_id', '')   # e.g. "award_42"

    _wh_logger.info("Payout webhook event=%s payout_id=%s ref=%s", event, payout_id, reference)

    if not payout_id:
        return JsonResponse({'status': 'ignored — no payout id'}, status=200)

    # ── Locate award ──────────────────────────────────────────────────────────
    from scholarships.models import ScholarshipAward

    award = None
    # Try by stored payout ID first
    try:
        award = ScholarshipAward.objects.get(razorpay_payout_id=payout_id)
    except ScholarshipAward.DoesNotExist:
        # Try by reference_id "award_<pk>"
        if reference.startswith('award_'):
            try:
                pk = int(reference.split('_')[1])
                award = ScholarshipAward.objects.get(pk=pk)
            except (ValueError, ScholarshipAward.DoesNotExist):
                pass

    if not award:
        _wh_logger.warning("Payout webhook: award not found for payout_id=%s ref=%s", payout_id, reference)
        return JsonResponse({'status': 'award not found'}, status=200)

    # ── Update transfer status ────────────────────────────────────────────────
    if event == 'payout.processed':
        award.transfer_status = 'DONE'
        award.razorpay_payout_id = payout_id
        award.save(update_fields=['transfer_status', 'razorpay_payout_id'])
        _wh_logger.info("Award %s marked DONE", award.pk)

    elif event in ('payout.failed', 'payout.reversed'):
        failure_reason = payout_obj.get('failure_reason', '') or event
        award.transfer_status = 'FAILED'
        award.failure_reason  = failure_reason
        award.razorpay_payout_id = payout_id
        award.save(update_fields=['transfer_status', 'failure_reason', 'razorpay_payout_id'])
        _wh_logger.warning("Award %s marked FAILED: %s", award.pk, failure_reason)

    else:
        _wh_logger.info("Payout webhook: unhandled event %s — ignored", event)

    return JsonResponse({'status': 'ok'}, status=200)
