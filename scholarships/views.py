from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Scholarship, RequiredDocument
from .recommendation import (
    passes_hard_filter,
    compute_match_score,
    get_eligibility_breakdown,
    DEGREE_TO_EDU_LEVEL,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_student_profile(user):
    """Return StudentProfile if user is a student, else None."""
    try:
        return user.studentprofile
    except Exception:
        return None


def _auto_edu_level(student_profile) -> str:
    """Return Scholarship.education_level key from student's latest AcademicRecord."""
    if not student_profile:
        return ''
    try:
        record = student_profile.academic_records.order_by('-id').first()
        if record:
            return DEGREE_TO_EDU_LEVEL.get(record.degree_level, '')
    except Exception:
        pass
    return ''


# ── Views ─────────────────────────────────────────────────────────────────────

@login_required
def scholarship_list(request):
    """Display active scholarships with search, filtering, and match scores."""
    scholarships_qs = Scholarship.objects.filter(is_active=True).select_related('org_profile')

    student = _get_student_profile(request.user)

    # ── Search ────────────────────────────────────────────────────────────────
    search_query = request.GET.get('search', '')
    if search_query:
        scholarships_qs = scholarships_qs.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(organization__icontains=search_query)
        )

    # ── Organization filter ───────────────────────────────────────────────────
    org_filter = request.GET.get('organization', '')
    if org_filter:
        scholarships_qs = scholarships_qs.filter(
            Q(organization__icontains=org_filter) |
            Q(org_profile__organization_name__icontains=org_filter)
        )

    # ── Education level filter (auto-apply from student profile if not set) ───
    edu_filter = request.GET.get('education', '')
    edu_auto_applied = False
    if not edu_filter and student and 'education' not in request.GET:
        auto = _auto_edu_level(student)
        if auto and auto != 'ANY':
            edu_filter = auto
            edu_auto_applied = True   # flag so template can show "auto" hint

    if edu_filter:
        # Show scholarships for this level + scholarships open to ANY
        scholarships_qs = scholarships_qs.filter(
            Q(education_level=edu_filter) | Q(education_level='ANY')
        )

    # ── Deadline filter ───────────────────────────────────────────────────────
    deadline_filter = request.GET.get('deadline', '')
    today = datetime.now().date()
    if deadline_filter == 'week':
        scholarships_qs = scholarships_qs.filter(
            deadline__gte=today, deadline__lte=today + timedelta(days=7))
    elif deadline_filter == 'month':
        scholarships_qs = scholarships_qs.filter(
            deadline__gte=today, deadline__lte=today + timedelta(days=30))
    elif deadline_filter == 'quarter':
        scholarships_qs = scholarships_qs.filter(
            deadline__gte=today, deadline__lte=today + timedelta(days=90))

    # ── DB-level sort ─────────────────────────────────────────────────────────
    sort_by = request.GET.get('sort', 'match')   # default: sort by match score
    valid_sorts = ['deadline', '-deadline', 'title', '-title',
                   'total_budget', '-total_budget', 'created_at', '-created_at']
    if sort_by in valid_sorts:
        scholarships_qs = scholarships_qs.order_by(sort_by)
    else:
        scholarships_qs = scholarships_qs.order_by('-created_at')

    # ── Materialise queryset + Layer 1 filter + Layer 2 scoring ──────────────
    scholarship_list_data = []
    for s in scholarships_qs:
        if student and not passes_hard_filter(student, s):
            continue
        if student:
            s.match_score = compute_match_score(student, s)
        else:
            s.match_score = None
        scholarship_list_data.append(s)

    # Sort by match score when requested (or as default for logged-in students)
    if sort_by == 'match' and student:
        scholarship_list_data.sort(key=lambda s: -(s.match_score or 0))

    # ── Sidebar data ──────────────────────────────────────────────────────────
    organizations = (
        Scholarship.objects.filter(is_active=True)
        .values_list('organization', flat=True).distinct()
    )
    from .models import EDUCATION_LEVEL_CHOICES
    edu_choices = EDUCATION_LEVEL_CHOICES

    context = {
        'scholarships':     scholarship_list_data,
        'organizations':    organizations,
        'edu_choices':      edu_choices,
        'total_count':      len(scholarship_list_data),
        'search_query':     search_query,
        'org_filter':       org_filter,
        'edu_filter':       edu_filter,
        'edu_auto_applied': edu_auto_applied,
        'deadline_filter':  deadline_filter,
        'sort_by':          sort_by,
        'is_student':       bool(student),
    }
    return render(request, 'scholarships/scholarship_list.html', context)


@login_required
def scholarship_detail(request, pk):
    """Display detailed scholarship info with eligibility tracker for students."""
    scholarship = get_object_or_404(Scholarship, pk=pk, is_active=True)
    required_docs = RequiredDocument.objects.filter(scholarship=scholarship)

    student = _get_student_profile(request.user)

    # Related scholarships — same education level first, then fallback
    related = Scholarship.objects.filter(
        is_active=True,
        education_level=scholarship.education_level,
    ).exclude(pk=pk).select_related('org_profile').order_by('-created_at')[:3]
    if not related.exists():
        related = Scholarship.objects.filter(
            is_active=True,
        ).exclude(pk=pk).order_by('-created_at')[:3]

    match_score  = None
    eligibility  = None
    if student:
        match_score = compute_match_score(student, scholarship)
        eligibility = get_eligibility_breakdown(student, scholarship)

    context = {
        'scholarship':       scholarship,
        'required_docs':     required_docs,
        'related_scholarships': related,
        'match_score':       match_score,
        'eligibility':       eligibility,
        'is_student':        bool(student),
    }
    return render(request, 'scholarships/scholarship_detail.html', context)


@login_required
def recommended_scholarships(request):
    """Personalised recommendations based on student profile."""
    student = _get_student_profile(request.user)
    all_qs = Scholarship.objects.filter(is_active=True).select_related('org_profile')

    recommendations = []
    for s in all_qs:
        if student and not passes_hard_filter(student, s):
            continue
        s.match_score = compute_match_score(student, s) if student else None
        recommendations.append(s)

    if student:
        recommendations.sort(key=lambda s: -(s.match_score or 0))

    context = {
        'scholarships': recommendations[:12],
        'is_student':   bool(student),
    }
    return render(request, 'scholarships/recommended.html', context)
