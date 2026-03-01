from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import json
import logging
import os
import re
import html as _html

logger = logging.getLogger(__name__)
from .models import Scholarship, RequiredDocument, ScholarshipCertificate
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

# Maps (degree_level, stream_keyword) → list of category strings for the API
# Order matters: more specific entries come first.
# Each entry can now yield MULTIPLE categories passed as comma-separated to the API.
_DEGREE_DOMAIN_MAP = [
    # (degree_level, stream_keyword, [category_list])
    ('Diploma',  'engineering', ['diploma', 'engineering', 'msbte']),
    ('Diploma',  'computer',   ['diploma', 'engineering', 'msbte']),
    ('Diploma',  None,         ['diploma', 'msbte']),
    ('10th',     None,         ['10th']),
    ('12th',     'science',    ['12th']),
    ('12th',     'commerce',   ['12th']),
    ('12th',     'arts',       ['12th']),
    ('12th',     None,         ['12th']),
    ('UG',       'engineering',['btech', 'engineering']),
    ('UG',       'medical',    ['medical']),
    ('UG',       'law',        ['law']),
    ('UG',       'management', ['bba']),
    ('UG',       None,         ['btech']),
    ('PG',       'engineering',['mtech', 'engineering']),
    ('PG',       'management', ['mba']),
    ('PG',       None,         ['mtech']),
    ('PhD',      None,         ['phd']),
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


def _detect_domains(student_profile):
    """
    Auto-detect a LIST of relevant API category strings from the student's
    AcademicRecord.  Returns e.g. ['diploma', 'engineering', 'msbte'].
    Falls back to ['btech'] when no profile / record is found.
    """
    if not student_profile:
        return ['btech']
    try:
        record = student_profile.academic_records.order_by('-id').first()
        if not record:
            return ['btech']
        degree = record.degree_level or ''
        stream = (record.stream or '').lower()

        for deg, stream_kw, categories in _DEGREE_DOMAIN_MAP:
            if deg == degree:
                if stream_kw is None or stream_kw in stream:
                    return list(categories)   # return a copy
    except Exception:
        pass
    return ['btech']


def _fetch_external_scholarships(categories):
    """
    Call the external scholarship search API with one or more category slugs.
    `categories` can be a list like ['diploma', 'engineering', 'msbte'] OR a
    plain string like 'btech'.  They are joined as a comma-separated value
    which the API supports natively.
    Returns (list_of_scholarships, total_found, error_message).
    """
    API_BASE = 'https://scholarship-4pxs.onrender.com/api/saved-scholarships/'
    if isinstance(categories, (list, tuple)):
        category_str = ','.join(categories)
    else:
        category_str = categories
    params = urllib.parse.urlencode({'category': category_str})
    url = f'{API_BASE}?{params}'
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
            scholarships = payload.get('data', [])
            total = payload.get('total_results', len(scholarships))
            return scholarships, total, None
    except Exception as exc:
        logger.warning(f'External scholarship API error for categories={category_str!r}: {exc}')
        return [], 0, str(exc)


@login_required
def external_scholarships(request):
    """Show live external scholarships fetched from the third-party API."""
    student = _get_student_profile(request.user)

    # Auto-detect a LIST of relevant categories from student profile
    auto_domains = _detect_domains(student)          # e.g. ['diploma', 'engineering', 'msbte']
    auto_domain_str = ','.join(auto_domains)          # 'diploma,engineering,msbte'

    # Manual override via ?category=slug1,slug2 in URL
    raw_param = request.GET.get('category', '').strip().lower()
    if raw_param:
        # Support comma-delimited multi-select from the pill UI
        selected_domains = [s.strip() for s in raw_param.split(',') if s.strip()]
        manual = True
    else:
        selected_domains = auto_domains
        manual = False

    domain_str = ','.join(selected_domains)           # passed to API

    scholarships, total_found, api_error = _fetch_external_scholarships(selected_domains)

    # ── Build student document map for Feature 3 ──────────────────────────────
    # Maps normalised keyword → {label, url, verified} so the template can
    # fuzzy-match any API doc name like "Aadhaar Card" or "Income certificate".
    DOC_KEYWORDS = {
        'aadhaar':      'aadhaar',
        'aadhar':       'aadhaar',
        'income':       'income_cert',
        'caste':        'caste_cert',
        'disability':   'disability_cert',
        'pwd':          'disability_cert',
        '10th':         'marksheet_10',
        'tenth':        'marksheet_10',
        'ssc':          'marksheet_10',
        '12th':         'marksheet_12',
        'twelfth':      'marksheet_12',
        'hsc':          'marksheet_12',
        'intermediate': 'marksheet_12',
        'marksheet':    'current_marksheet',
        'semester':     'current_marksheet',
        'current':      'current_marksheet',
        'bank':         'bank_passbook',
        'passbook':     'bank_passbook',
        'photo':        'photo',
        'passport':     'photo',
    }

    student_doc_map = {}   # keyword → {label, url, verified}
    if student:
        from users.models import StudentDocument
        docs_qs = StudentDocument.objects.filter(student=student).select_related()
        doc_by_type = {d.document_type: d for d in docs_qs}
        for keyword, doc_type in DOC_KEYWORDS.items():
            if doc_type in doc_by_type:
                doc = doc_by_type[doc_type]
                student_doc_map[keyword] = {
                    'label':    doc.get_document_type_display(),
                    'url':      doc.file.url if doc.file else None,
                    'verified': doc.is_verified,
                }

    context = {
        'scholarships':       scholarships,
        'total_found':        total_found,
        # For display/URL building
        'selected_domains':   selected_domains,       # list of active slugs
        'domain_str':         domain_str,             # comma-joined active
        'auto_domains':       auto_domains,           # list auto-detected
        'auto_domain_str':    auto_domain_str,        # for display
        'manual_domain':      manual,
        'api_error':          api_error,
        'domain_options':     DOMAIN_OPTIONS,
        'is_student':         bool(student),
        # Feature 3: keyword → doc info map (JSON-serialised for JS use)
        'student_doc_map_json': json.dumps(student_doc_map),
    }
    return render(request, 'scholarships/external_scholarships.html', context)



# ── Scholarship AI Guide (AJAX endpoint) ─────────────────────────────────────

def _resolve_real_url(rss_url, timeout=10):
    """Follow redirects from a Google News RSS URL to the actual scholarship page."""
    try:
        req = urllib.request.Request(
            rss_url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; ScholarMatch/1.0)'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.url          # final URL after all redirects
    except Exception:
        return rss_url              # fallback: return original


def _fetch_page_text(url, max_chars=3000, timeout=12):
    """Fetch a web page and return plain-text content (HTML tags stripped)."""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; ScholarMatch/1.0)'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(120_000)                          # 120 KB max
            enc = resp.headers.get_content_charset('utf-8')
            html_text = raw.decode(enc, errors='replace')
        # Strip <script> and <style> blocks first, then all tags
        html_text = re.sub(r'<script[^>]*>.*?</script>', ' ', html_text,
                           flags=re.DOTALL | re.IGNORECASE)
        html_text = re.sub(r'<style[^>]*>.*?</style>', ' ', html_text,
                           flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', html_text)
        text = _html.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars]
    except Exception as exc:
        logger.warning(f'Page fetch failed for {url!r}: {exc}')
        return ''


def _call_ai_guide(prompt):
    """
    Call Groq API trying multiple models.
    Uses browser-like headers to bypass Cloudflare bot detection (error 1010).
    """
    import urllib.error
    groq_key = os.environ.get('GROQ_API_KEY', '').strip()
    if not groq_key:
        raise ValueError('GROQ_API_KEY not set in .env — restart the server after adding it.')

    # Browser-like headers required to pass Cloudflare bot detection on api.groq.com
    GROQ_HEADERS = {
        'Authorization':  f'Bearer {groq_key}',
        'Content-Type':   'application/json',
        'User-Agent':     ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/122.0.0.0 Safari/537.36'),
        'Accept':         'application/json,*/*',
        'Accept-Language':'en-US,en;q=0.9',
        'Origin':         'https://console.groq.com',
        'Referer':        'https://console.groq.com/',
    }

    models_to_try = [
        'llama-3.3-70b-versatile',
        'llama3-8b-8192',
        'llama-3.1-8b-instant',
    ]
    last_error = 'No models attempted.'
    for model in models_to_try:
        body = json.dumps({
            'model':       model,
            'messages':    [{'role': 'user', 'content': prompt}],
            'max_tokens':  1400,
            'temperature': 0.4,
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=body,
            headers=GROQ_HEADERS,
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                logger.info(f'Groq OK with model={model}')
                return data['choices'][0]['message']['content'].strip()
        except urllib.error.HTTPError as e:
            raw = e.read().decode('utf-8', errors='replace')
            logger.error(f'Groq {e.code} ({model}) raw: {raw[:400]}')
            try:
                msg = json.loads(raw).get('error', {}).get('message', raw[:200])
            except Exception:
                msg = raw[:200] or str(e)
            last_error = f'Groq {e.code} ({model}): {msg}'
            continue
        except Exception as exc:
            logger.error(f'Groq error ({model}): {exc}')
            last_error = str(exc)
            continue

    raise ValueError(last_error)



def _parse_ai_response(text):
    """Parse the structured AI response into a dict of sections."""
    result = {
        'eligible':        'maybe',
        'eligible_reason': 'Could not determine eligibility.',
        'steps':           [],
        'pros':            [],
        'cons':            [],
    }
    if not text:
        return result

    # ELIGIBILITY line
    m = re.search(
        r'ELIGIBILITY\s*:\s*(ELIGIBLE|NOT_ELIGIBLE|UNCLEAR)\s*\|\s*(.+)',
        text, re.IGNORECASE
    )
    if m:
        v = m.group(1).upper()
        result['eligible'] = 'yes' if v == 'ELIGIBLE' else ('no' if v == 'NOT_ELIGIBLE' else 'maybe')
        result['eligible_reason'] = m.group(2).strip()

    # HOW_TO_APPLY numbered steps
    how = re.search(r'HOW_TO_APPLY\s*:(.*?)(?=PROS\s*:|CONS\s*:|$)', text, re.DOTALL | re.IGNORECASE)
    if how:
        result['steps'] = [s.strip() for s in re.findall(r'\d+\.\s*(.+)', how.group(1)) if s.strip()]

    # PROS bullet list
    pros = re.search(r'PROS\s*:(.*?)(?=CONS\s*:|HOW_TO_APPLY\s*:|$)', text, re.DOTALL | re.IGNORECASE)
    if pros:
        result['pros'] = [p.strip() for p in re.findall(r'-\s*(.+)', pros.group(1)) if p.strip()]

    # CONS bullet list
    cons = re.search(r'CONS\s*:(.*?)(?=PROS\s*:|HOW_TO_APPLY\s*:|$)', text, re.DOTALL | re.IGNORECASE)
    if cons:
        result['cons'] = [c.strip() for c in re.findall(r'-\s*(.+)', cons.group(1)) if c.strip()]

    return result


def _get_youtube_video_id(query, timeout=8):
    """
    Search YouTube (no API key) and return the first embeddable-looking video ID.
    Scrapes ytInitialData JSON embedded in the search page.
    Returns a video_id string or None on failure.
    """
    try:
        search_url = f'https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}&hl=en'
        req = urllib.request.Request(
            search_url,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/122.0.0.0 Safari/537.36'
                ),
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read(300_000).decode('utf-8', errors='replace')

        # Extract all 11-char video IDs from ytInitialData JSON
        ids = re.findall(r'"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"', html)

        # Deduplicate while preserving order
        seen = set()
        unique_ids = []
        for vid in ids:
            if vid not in seen:
                seen.add(vid)
                unique_ids.append(vid)

        # Skip the very first ID (often a promoted/mix/ad result),
        # return the 2nd unique ID as it's typically a real video result.
        # Fall back to first if only one found.
        if len(unique_ids) >= 2:
            return unique_ids[1]
        elif unique_ids:
            return unique_ids[0]
    except Exception as exc:
        logger.warning(f'YouTube scrape failed for {query!r}: {exc}')
    return None


@login_required
def external_scholarship_guide(request):
    """
    AJAX POST endpoint: generate AI scholarship guidance for the logged-in student.
    Body JSON: {scholarship_url, scholarship_title, scholarship_info, documents_required[]}
    Response JSON: {eligible, eligible_reason, steps[], pros[], cons[], youtube_url, real_url, error}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    scholarship_url   = body.get('scholarship_url', '')
    scholarship_title = body.get('scholarship_title', 'this scholarship')
    scholarship_info  = body.get('scholarship_info', '')
    docs_required     = body.get('documents_required', [])

    # ── Step A: resolve real URL + fetch page content ─────────────────────────
    real_url  = _resolve_real_url(scholarship_url) if scholarship_url else ''
    page_text = _fetch_page_text(real_url)          if real_url       else ''

    # ── Step B: build student profile context ─────────────────────────────────
    student = _get_student_profile(request.user)
    student_ctx = 'Not available (student profile missing).'
    if student:
        rec = student.academic_records.order_by('-id').first()
        student_ctx = (
            f"Name: {student.full_name}\n"
            f"Caste/Category: {student.caste_category or 'Not specified'}\n"
            f"Annual Family Income: ₹{student.annual_income or 'Not specified'}\n"
            f"City/State: {student.city or '—'}, {student.state or '—'}\n"
            f"Person with Disability: {'Yes' if student.is_disabled else 'No'}\n"
            f"Degree Level: {rec.degree_level if rec else 'Not specified'}\n"
            f"Stream: {rec.stream if rec else 'Not specified'}\n"
            f"Institution: {rec.institution_name if rec else 'Not specified'}\n"
            f"Last Exam Score: {rec.last_exam_score if rec else 'N/A'}%"
        )

    # ── Step C: build prompt ──────────────────────────────────────────────────
    docs_str = '\n'.join(f'  - {d}' for d in docs_required) if docs_required else '  (not listed)'
    prompt = f"""You are an expert Indian scholarship advisor. Analyze the following scholarship for a student and give structured advice.

STUDENT PROFILE:
{student_ctx}

SCHOLARSHIP: {scholarship_title}
BRIEF INFO: {scholarship_info[:500]}

OFFICIAL PAGE CONTENT (auto-extracted):
{page_text if page_text else '(Could not load page — use the scholarship title and brief info only)'}

REQUIRED DOCUMENTS:
{docs_str}

Respond in EXACTLY this format — use these headers verbatim, no extra text outside them:

ELIGIBILITY: [ELIGIBLE or NOT_ELIGIBLE or UNCLEAR] | [One sentence: why the student is/isn't eligible based on their profile above]

HOW_TO_APPLY:
1. [Specific step]
2. [Specific step]
3. [Specific step]
4. [Specific step]
5. [Specific step]

PROS:
- [Advantage of this scholarship]
- [Advantage]
- [Advantage]

CONS:
- [Limitation or watch-out]
- [Limitation]
- [Limitation]

Keep points concise (1 sentence each). Focus on India-specific practical advice."""

    # ── Step D: call AI ───────────────────────────────────────────────────────
    ai_error = None
    try:
        ai_text = _call_ai_guide(prompt)
    except Exception as exc:
        logger.error(f'AI guide FAILED — {type(exc).__name__}: {exc}')
        ai_text  = None
        ai_error = f'AI guide error: {type(exc).__name__} — {str(exc)[:120]}'

    parsed = _parse_ai_response(ai_text)

    # ── Step E: YouTube — search and build thumbnail + watch + embed URLs ────────
    yt_query   = f'{scholarship_title} scholarship how to apply India'
    video_id   = _get_youtube_video_id(yt_query)
    if video_id:
        yt_embed     = f'https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1&autoplay=1'
        yt_watch     = f'https://www.youtube.com/watch?v={video_id}'
        yt_thumbnail = f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'
    else:
        yt_embed     = None
        yt_thumbnail = None
        yt_watch     = f'https://www.youtube.com/results?search_query={urllib.parse.quote_plus(yt_query)}'

    return JsonResponse({
        **parsed,
        'youtube_embed_url': yt_embed,
        'youtube_thumbnail': yt_thumbnail,
        'youtube_url':       yt_watch,
        'real_url':          real_url or scholarship_url,
        'error':             ai_error,
    })


# ── Certificate Verification (PUBLIC — no login required) ─────────────────────────────────

def verify_certificate(request, cert_uuid):
    """
    Public verification endpoint.
    Anyone can visit /scholarships/certificates/verify/<uuid>/ to check
    whether a certificate is genuine and view all real details.
    No authentication required.
    """
    cert = get_object_or_404(ScholarshipCertificate, certificate_id=cert_uuid)
    context = {
        'cert':        cert,
        'award':       cert.award,
        'student':     cert.award.student,
        'scholarship': cert.award.scholarship,
        'org_name':    (
            cert.award.scholarship.org_profile.organization_name
            if cert.award.scholarship.org_profile
            else cert.award.scholarship.organization or 'Scholar Match'
        ),
    }
    return render(request, 'scholarships/certificate_verify.html', context)
