from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger(__name__)
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


# ── External Scholarships (via external API) ──────────────────────────────────

# Maps (degree_level, stream_keyword) → category string for the API
_DEGREE_DOMAIN_MAP = [
    ('Diploma',  None,          'diploma'),
    ('10th',     None,          '10th'),
    ('12th',     'science',     '12th'),
    ('12th',     'commerce',    '12th'),
    ('12th',     'arts',        '12th'),
    ('12th',     None,          '12th'),
    ('UG',       'engineering', 'btech'),
    ('UG',       'medical',     'medical'),
    ('UG',       'law',         'law'),
    ('UG',       'management',  'bba'),
    ('UG',       None,          'btech'),
    ('PG',       'engineering', 'mtech'),
    ('PG',       'management',  'mba'),
    ('PG',       None,          'mtech'),
    ('PhD',      None,          'phd'),
]

# Quick list shown as switcher pills on the page
DOMAIN_OPTIONS = [
    ('diploma',  'Diploma'),
    ('btech',    'B.Tech'),
    ('mtech',    'M.Tech'),
    ('mba',      'MBA'),
    ('bba',      'BBA'),
    ('medical',  'Medical'),
    ('law',      'Law'),
    ('phd',      'PhD'),
    ('12th',     '12th Pass'),
]


def _detect_domain(student_profile):
    """Auto-detect the best API category string from student's AcademicRecord."""
    if not student_profile:
        return 'btech'
    try:
        record = student_profile.academic_records.order_by('-id').first()
        if not record:
            return 'btech'
        degree = record.degree_level or ''
        stream = (record.stream or '').lower()

        for deg, stream_kw, category in _DEGREE_DOMAIN_MAP:
            if deg == degree:
                if stream_kw is None or stream_kw in stream:
                    return category
    except Exception:
        pass
    return 'btech'


def _fetch_external_scholarships(category):
    """
    Call the external scholarship search API.
    Returns (list_of_scholarships, total_found, error_message).
    """
    API_BASE = 'https://scholarship-4pxs.onrender.com/api/saved-scholarships/'
    params = urllib.parse.urlencode({'category': category})
    url = f'{API_BASE}?{params}'
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
            scholarships = payload.get('data', [])
            total = payload.get('total_results', len(scholarships))
            return scholarships, total, None
    except Exception as exc:
        logger.warning(f'External scholarship API error for category={category!r}: {exc}')
        return [], 0, str(exc)


@login_required
def external_scholarships(request):
    """Show live external scholarships fetched from the third-party API."""
    student = _get_student_profile(request.user)

    # Determine category: manual override > auto-detected from profile
    auto_domain = _detect_domain(student)
    domain = request.GET.get('category', '').strip().lower() or auto_domain
    manual = (domain != auto_domain)

    scholarships, total_found, api_error = _fetch_external_scholarships(domain)

    context = {
        'scholarships':    scholarships,
        'total_found':     total_found,
        'domain':          domain,
        'auto_domain':     auto_domain,
        'manual_domain':   manual,
        'api_error':       api_error,
        'domain_options':  DOMAIN_OPTIONS,
        'is_student':      bool(student),
    }
    return render(request, 'scholarships/external_scholarships.html', context)
