"""
scholarships/award_engine.py
────────────────────────────
Phase 7D — Merit Score Engine

Four public functions:
  1. eligibility_gate(application)        → bool
  2. compute_merit_score(application)     → float (0–100)
  3. get_merit_list(scholarship)          → list[dict]   ranked
  4. auto_approve_winners(scholarship)    → list[ScholarshipAward]
"""
from __future__ import annotations

import logging
from django.utils import timezone
from django.db.models import Sum

logger = logging.getLogger(__name__)

# ─── Merit weight constants ───────────────────────────────────────────────────
WEIGHT_ACADEMIC = 35   # last sem marks %
WEIGHT_NEED     = 40   # 1 − (prior_scholarships / total_fees)   → more need = higher score
WEIGHT_INCOME   = 25   # 1 − (annual_income / max_income_cap)    → lower income = higher score

MAX_INCOME_CAP  = 1_200_000   # Rs. 12 lakh — above this income score = 0


# ─── 1. Eligibility gate ──────────────────────────────────────────────────────
def eligibility_gate(application) -> bool:
    """
    Returns True only when the application meets the minimum data quality bar
    required to appear on the merit list.

    Gates:
    - Application must not be REJECTED or DRAFT
    - MarksheetVerification must exist and be Gemini-verified
    - FeesVerification must exist, be Gemini-verified, and college_match = True
    """
    try:
        if application.status in ('DRAFT', 'REJECTED'):
            return False

        student = application.student

        # Marksheet check
        try:
            mv = student.marksheet_verification
        except Exception:
            return False
        if not mv.gemini_verified or mv.last_sem_marks is None:
            return False

        # Fees receipt check
        try:
            fv = student.fees_verification
        except Exception:
            return False
        if not fv.gemini_verified or not fv.college_match or fv.total_annual_fees is None:
            return False

        return True

    except Exception as exc:
        logger.warning("eligibility_gate error for application %s: %s", getattr(application, 'pk', '?'), exc)
        return False


# ─── 2. Merit score ───────────────────────────────────────────────────────────
def compute_merit_score(application) -> float:
    """
    Computes a 0–100 merit score for an application.

    Formula:
        academic_score  = (last_sem_marks / 100) × 35
        need_score      = (1 − prior_received / total_fees) × 40
        income_score    = (1 − annual_income / MAX_INCOME_CAP) × 25
        total           = academic_score + need_score + income_score

    Returns 0.0 on any data error (application still won't appear on merit list
    unless eligibility_gate also passes).
    """
    try:
        student = application.student

        # ── Academic score (35 pts) ───────────────────────────────────────────
        try:
            marks = float(student.marksheet_verification.last_sem_marks or 0)
        except Exception:
            marks = 0.0
        marks = max(0.0, min(100.0, marks))
        academic_score = (marks / 100.0) * WEIGHT_ACADEMIC

        # ── Need score (40 pts) ───────────────────────────────────────────────
        try:
            total_fees = float(student.fees_verification.total_annual_fees or 0)
        except Exception:
            total_fees = 0.0

        if total_fees > 0:
            # Sum of amounts across all DONE ScholarshipAwards for this student
            from scholarships.models import ScholarshipAward
            prior_received = float(
                ScholarshipAward.objects
                .filter(student=student, transfer_status='DONE')
                .exclude(pk=getattr(application, 'award', None) and application.award.pk)
                .aggregate(total=Sum('amount_awarded'))['total'] or 0
            )
            coverage_ratio = min(1.0, prior_received / total_fees)
        else:
            coverage_ratio = 0.0   # No fees data → treat as fully uncovered (max need)

        need_score = (1.0 - coverage_ratio) * WEIGHT_NEED

        # ── Income score (25 pts) ─────────────────────────────────────────────
        try:
            income = float(student.annual_income or 0)
        except Exception:
            income = 0.0
        income = max(0.0, income)
        if income >= MAX_INCOME_CAP:
            income_ratio = 1.0
        else:
            income_ratio = income / MAX_INCOME_CAP
        income_score = (1.0 - income_ratio) * WEIGHT_INCOME

        total = round(academic_score + need_score + income_score, 2)
        return max(0.0, min(100.0, total))

    except Exception as exc:
        logger.warning("compute_merit_score error for application %s: %s",
                       getattr(application, 'pk', '?'), exc)
        return 0.0


# ─── 3. Merit list ────────────────────────────────────────────────────────────
def get_merit_list(scholarship) -> list[dict]:
    """
    Returns a ranked list of eligible applications for a scholarship.
    Each dict contains:
        rank, application, student, merit_score,
        marks, fees, prior_received, income,
        marksheet_verified, fees_verified, college_match
    Tied scores are broken by: marks desc → income asc → application date asc.
    """
    from applications.models import Application

    applications = (
        Application.objects
        .filter(scholarship=scholarship)
        .exclude(status__in=['DRAFT', 'REJECTED'])
        .select_related('student', 'student__marksheet_verification', 'student__fees_verification')
        .order_by('last_action_date')
    )

    scored = []
    for app in applications:
        if not eligibility_gate(app):
            continue
        score = compute_merit_score(app)
        student = app.student

        try:
            marks = float(student.marksheet_verification.last_sem_marks or 0)
            marksheet_verified = student.marksheet_verification.gemini_verified
        except Exception:
            marks = 0.0
            marksheet_verified = False

        try:
            fees = float(student.fees_verification.total_annual_fees or 0)
            fees_verified = student.fees_verification.gemini_verified
            college_match = student.fees_verification.college_match
        except Exception:
            fees = 0.0
            fees_verified = False
            college_match = False

        try:
            income = float(student.annual_income or 0)
        except Exception:
            income = 0.0

        from scholarships.models import ScholarshipAward
        prior = float(
            ScholarshipAward.objects
            .filter(student=student, transfer_status='DONE')
            .aggregate(total=Sum('amount_awarded'))['total'] or 0
        )

        scored.append({
            'application':        app,
            'student':            student,
            'merit_score':        score,
            'marks':              marks,
            'fees':               fees,
            'prior_received':     prior,
            'income':             income,
            'marksheet_verified': marksheet_verified,
            'fees_verified':      fees_verified,
            'college_match':      college_match,
        })

    # Sort: merit_score desc, marks desc, income asc, application date asc (FIFO)
    scored.sort(key=lambda x: (-x['merit_score'], -x['marks'], x['income'],
                               x['application'].last_action_date))

    # Assign ranks
    for rank, entry in enumerate(scored, start=1):
        entry['rank'] = rank

    return scored


# ─── 4. Auto-approve winners ──────────────────────────────────────────────────
def auto_approve_winners(scholarship) -> list:
    """
    Creates ScholarshipAward records for the top N applicants on the merit list
    (N = scholarship.num_winners).

    - Skips students who already have a ScholarshipAward for this scholarship.
    - Sets award amount based on scholarship.distribution_type:
        FIXED   → scholarship.fixed_amount per winner
        DYNAMIC → remaining escrow budget / num_winners (equal split)
    - Sets transfer_status = 'APPROVED'
    - Updates Application.status → 'APPROVED'
    Returns list of created ScholarshipAward instances.
    """
    from scholarships.models import ScholarshipAward
    from django.utils import timezone

    num_winners = scholarship.num_winners or 1
    merit_list  = get_merit_list(scholarship)
    top_entries = merit_list[:num_winners]

    if not top_entries:
        logger.info("auto_approve_winners: no eligible applicants for %s", scholarship)
        return []

    # Determine per-winner amount
    if scholarship.distribution_type == 'FIXED':
        per_winner_amount = scholarship.fixed_amount or 0
    else:
        # DYNAMIC: split remaining budget equally
        existing_disbursed = (
            ScholarshipAward.objects
            .filter(scholarship=scholarship)
            .aggregate(total=Sum('amount_awarded'))['total'] or 0
        )
        total_budget_rs = (scholarship.total_budget or 0)
        remaining = max(0, total_budget_rs - existing_disbursed)
        per_winner_amount = remaining // num_winners if num_winners else 0

    created_awards = []
    now = timezone.now()

    for entry in top_entries:
        application = entry['application']
        student = entry['student']

        # Skip if already awarded
        if ScholarshipAward.objects.filter(application=application).exists():
            logger.info("award already exists for application %s, skipping", application.pk)
            continue

        award = ScholarshipAward.objects.create(
            application      = application,
            scholarship      = scholarship,
            student          = student,
            merit_score      = entry['merit_score'],
            merit_rank       = entry['rank'],
            marks_at_award   = entry['marks'] or None,
            fees_at_award    = int(entry['fees']) if entry['fees'] else None,
            prior_received   = int(entry['prior_received']),
            amount_awarded   = per_winner_amount,
            transfer_status  = 'APPROVED',
        )
        created_awards.append(award)

        # Update application status
        application.status = 'APPROVED'
        application.save(update_fields=['status'])

        logger.info(
            "ScholarshipAward created: rank=%d student=%s amount=Rs.%d",
            entry['rank'], student, per_winner_amount
        )

    return created_awards


# ─── 5. Trigger bank transfer (DEMO MODE — no real money) ────────────────────
def trigger_bank_transfer(award) -> str:
    """
    DEMO MODE: Instantly marks the award as DONE without hitting Razorpay.

    Replace this function body with the Razorpay Payouts implementation
    once the Payouts product is enabled on your account.

    Returns: a mock payout ID string.
    """
    from django.utils import timezone
    import uuid

    mock_payout_id = f"mock_pout_{uuid.uuid4().hex[:12]}"

    award.razorpay_payout_id    = mock_payout_id
    award.transfer_status       = 'DONE'
    award.transfer_initiated_at = timezone.now()
    award.transfer_completed_at = timezone.now()
    award.save(update_fields=[
        'razorpay_payout_id', 'transfer_status',
        'transfer_initiated_at', 'transfer_completed_at'
    ])

    logger.info(
        "DEMO transfer complete: award %s | student %s | Rs.%s | mock_id=%s",
        award.pk, award.student, award.amount_awarded, mock_payout_id
    )
    return mock_payout_id
