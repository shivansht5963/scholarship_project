"""
scholarships/recommendation.py

Core scholarship recommendation engine.

Provides:
    DEGREE_TO_EDU_LEVEL      — Gap 1 fix: maps AcademicRecord.degree_level
                               to Scholarship.education_level choice values.

    passes_hard_filter()     — Layer 1: returns False the moment any hard
                               eligibility criterion fails. Scholarships that
                               fail are never shown to the student.

    compute_match_score()    — Layer 2: returns 0-100 weighted match score.
                               Higher = better fit. Used for sorting + badge.

    get_eligibility_breakdown() — Returns per-criterion pass/fail dict for the
                               eligibility tracker widget on the detail page.
"""

from __future__ import annotations
import logging

from .pin_classifier import student_location_tags

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# GAP 1 FIX — Education level normalisation
# ─────────────────────────────────────────────────────────────────────────────

# Maps AcademicRecord.degree_level  →  Scholarship.education_level choice key
DEGREE_TO_EDU_LEVEL: dict[str, str] = {
    "10th":    "HIGH_SCHOOL",
    "12th":    "HIGH_SCHOOL",
    "Diploma": "DIPLOMA",
    "UG":      "UG",
    "PG":      "PG",
    "PhD":     "PHD",
}


def _get_latest_record(student_profile):
    """Return most recent AcademicRecord for a student, or None."""
    try:
        return student_profile.academic_records.order_by("-id").first()
    except Exception:
        return None


def _student_edu_level(student_profile) -> str:
    """Resolve the Scholarship.education_level key for a student's latest record."""
    record = _get_latest_record(student_profile)
    if record:
        return DEGREE_TO_EDU_LEVEL.get(record.degree_level, "")
    return ""


def _student_score(student_profile):
    """Return latest academic score as Decimal, or None."""
    record = _get_latest_record(student_profile)
    return record.last_exam_score if record else None


def _student_stream(student_profile) -> str:
    """Return stream/course from latest academic record (lowercase)."""
    record = _get_latest_record(student_profile)
    return (record.stream or "").strip().lower() if record else ""


def _student_demographic_tags(student_profile) -> set[str]:
    """
    Collect all demographic tags that apply to a student.
    Matches against Scholarship.demographic_focus JSON list values.
    """
    tags: set[str] = set()

    # Gender
    gender = (getattr(student_profile, "gender", "") or "").lower()
    if gender == "female":
        tags.add("women")

    # Caste
    caste = (getattr(student_profile, "caste_category", "") or "").upper()
    caste_map = {"SC": "SC", "ST": "ST", "OBC": "OBC", "EWS": "EWS"}
    if caste in caste_map:
        tags.add(caste_map[caste])

    # Disability
    if getattr(student_profile, "is_disabled", False):
        tags.add("disabled")

    # Location (tier2 / rural) — from pin_classifier
    tags |= student_location_tags(student_profile)

    return tags


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 1 — Hard eligibility filter
# ─────────────────────────────────────────────────────────────────────────────

def passes_hard_filter(student_profile, scholarship) -> bool:
    """
    Returns True only when the student satisfies ALL hard eligibility rules.
    Any single failure returns False immediately.

    Hard rules (blocking):
        1. Education level must match (unless scholarship is 'ANY')
        2. Family income must be within the scholarship's maximum
        3. Academic score must meet the scholarship's minimum
        4. Karma must meet the scholarship's minimum
    """
    try:
        # 1 — Education level
        if scholarship.education_level and scholarship.education_level != "ANY":
            student_level = _student_edu_level(student_profile)
            if student_level and student_level != scholarship.education_level:
                return False

        # 2 — Family income
        if scholarship.max_family_income and student_profile.annual_income:
            if student_profile.annual_income > scholarship.max_family_income:
                return False

        # 3 — Academic score
        if scholarship.min_percentage:
            score = _student_score(student_profile)
            if score is not None and score < scholarship.min_percentage:
                return False

        # 4 — Karma
        if scholarship.min_karma:
            if student_profile.total_karma_points < scholarship.min_karma:
                return False

    except Exception as exc:
        logger.warning("passes_hard_filter error for student %s: %s", student_profile, exc)
        # Fail open — show scholarship rather than hide it on error
        return True

    return True


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 2 — Weighted match score (0-100)
# ─────────────────────────────────────────────────────────────────────────────

def compute_match_score(student_profile, scholarship) -> int:
    """
    Returns an integer 0-100 representing how well the student matches
    this scholarship. Higher = better fit.

    Breakdown (max points):
        Academic score       30 pts
        Family income        20 pts  (lower income relative to cap = higher pts)
        Course/stream match  20 pts
        Demographic tags     20 pts  (5 pts per matching tag, max 4 tags)
        Karma bonus          10 pts
    """
    score = 0

    try:
        # ── Academic score (max 30) ───────────────────────────────────────────
        student_score = _student_score(student_profile)
        if student_score is not None:
            if scholarship.min_percentage:
                if student_score >= scholarship.min_percentage:
                    score += int(30 * float(student_score) / 100)
            else:
                # No minimum set — award full proportion
                score += int(30 * float(student_score) / 100)

        # ── Family income (max 20) ────────────────────────────────────────────
        income = getattr(student_profile, "annual_income", None)
        if scholarship.max_family_income and income is not None:
            cap = float(scholarship.max_family_income)
            if cap > 0:
                ratio = 1.0 - (float(income) / cap)
                score += int(20 * max(0.0, min(1.0, ratio)))
        else:
            # No income cap — all students get 10 base pts (neutral)
            score += 10

        # ── Course / stream match (max 20) ────────────────────────────────────
        scholarship_courses = [c.strip().lower() for c in scholarship.get_courses()]
        if scholarship_courses:
            student_s = _student_stream(student_profile)
            if student_s:
                if student_s in scholarship_courses:
                    score += 20                       # exact match
                elif any(student_s in c or c in student_s for c in scholarship_courses):
                    score += 10                       # partial match
                # else: 0 (no match)
            else:
                score += 10                           # unknown stream — partial credit
        else:
            score += 20                               # open to all courses

        # ── Demographic tags (max 20, 5 pts each, max 4 tags) ────────────────
        student_tags = _student_demographic_tags(student_profile)
        scholarship_demos = {d.strip().lower() for d in scholarship.get_demographic_focus()}
        if scholarship_demos:
            matched = student_tags & scholarship_demos
            score += min(20, len(matched) * 5)
        else:
            # No demographic focus — all students get full 20
            score += 20

        # ── Karma bonus (max 10) ──────────────────────────────────────────────
        karma = getattr(student_profile, "total_karma_points", 0) or 0
        score += min(10, int(karma / 500 * 10))

    except Exception as exc:
        logger.warning("compute_match_score error for student %s: %s", student_profile, exc)
        return 0

    return max(0, min(100, score))


# ─────────────────────────────────────────────────────────────────────────────
# ELIGIBILITY BREAKDOWN — for the detail page tracker widget
# ─────────────────────────────────────────────────────────────────────────────

def get_eligibility_breakdown(student_profile, scholarship) -> dict:
    """
    Returns a dict with per-criterion pass/fail flags and display values.
    Used by scholarship_detail.html to render the eligibility tracker widget.

    Return shape:
    {
        "education": {"passed": bool, "student_value": str, "required_value": str},
        "income":    {"passed": bool, "student_value": str, "required_value": str},
        "score":     {"passed": bool, "student_value": str, "required_value": str},
        "karma":     {"passed": bool, "student_value": str, "required_value": str},
        "documents": {"passed": bool, "student_value": str, "required_value": str},
        "overall":   bool,   # True only if all criteria pass
    }
    """
    breakdown = {}

    try:
        # ── Education level ───────────────────────────────────────────────────
        req_edu = scholarship.education_level
        student_edu = _student_edu_level(student_profile)
        edu_passed = (req_edu == "ANY") or (not student_edu) or (student_edu == req_edu)
        breakdown["education"] = {
            "passed": edu_passed,
            "student_value": student_edu or "Not specified",
            "required_value": scholarship.get_education_level_display(),
        }

        # ── Family income ─────────────────────────────────────────────────────
        income = getattr(student_profile, "annual_income", None)
        max_inc = scholarship.max_family_income
        if max_inc:
            inc_passed = (income is None) or (float(income) <= float(max_inc))
            student_inc_str = f"Rs.{int(income):,}" if income else "Not provided"
            req_inc_str = f"Rs.{max_inc:,} max"
        else:
            inc_passed = True
            student_inc_str = f"Rs.{int(income):,}" if income else "Not provided"
            req_inc_str = "No limit"
        breakdown["income"] = {
            "passed": inc_passed,
            "student_value": student_inc_str,
            "required_value": req_inc_str,
        }

        # ── Academic score ────────────────────────────────────────────────────
        s_score = _student_score(student_profile)
        min_pct = scholarship.min_percentage
        if min_pct:
            score_passed = (s_score is None) or (s_score >= min_pct)
            req_score_str = f"{min_pct}% min"
        else:
            score_passed = True
            req_score_str = "No minimum"
        breakdown["score"] = {
            "passed": score_passed,
            "student_value": f"{s_score}%" if s_score else "Not provided",
            "required_value": req_score_str,
        }

        # ── Karma ─────────────────────────────────────────────────────────────
        karma = getattr(student_profile, "total_karma_points", 0) or 0
        min_karma = scholarship.min_karma or 0
        karma_passed = karma >= min_karma
        breakdown["karma"] = {
            "passed": karma_passed,
            "student_value": f"{karma} pts",
            "required_value": f"{min_karma} pts min",
        }

        # ── Documents ─────────────────────────────────────────────────────────
        # Check how many required docs the student has already uploaded
        from .models import RequiredDocument
        required_doc_types = set(
            RequiredDocument.objects.filter(scholarship=scholarship)
            .values_list("document_name", flat=True)
        )
        uploaded_doc_types = set(
            student_profile.documents
            .filter(is_verified=False)       # include unverified too
            .values_list("document_type", flat=True)
        )
        # Map scholarship doc names to student doc types where possible
        common_map = {
            "income_certificate": "income_cert",
            "marksheet": "current_marksheet",
            "college_id": "other",
            "aadhaar": "aadhaar",
            "caste_certificate": "caste_cert",
            "bank_passbook": "bank_passbook",
            "disability_cert": "disability_cert",
            "domicile_certificate": "other",
            "photo": "photo",
        }
        matched_docs = sum(
            1 for d in required_doc_types
            if common_map.get(d, d) in uploaded_doc_types
        )
        total_docs = len(required_doc_types)
        docs_passed = (total_docs == 0) or (matched_docs >= total_docs)
        breakdown["documents"] = {
            "passed": docs_passed,
            "student_value": f"{matched_docs}/{total_docs} uploaded" if total_docs else "None required",
            "required_value": f"{total_docs} document(s)",
        }

        # ── Overall ───────────────────────────────────────────────────────────
        breakdown["overall"] = all(
            v["passed"] for k, v in breakdown.items() if isinstance(v, dict)
        )

    except Exception as exc:
        logger.warning("get_eligibility_breakdown error: %s", exc)
        breakdown.setdefault("overall", False)

    return breakdown
