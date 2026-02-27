"""
scholarships/templatetags/scholarship_tags.py

Custom Django template filters & tags for the scholarship recommendation UI.

Load in templates with:
    {% load scholarship_tags %}

Available filters:
    match_color     : int  -> CSS class suffix  ('green'|'yellow'|'orange'|'red')
    match_label     : int  -> human label       ('Excellent'|'Good'|'Partial'|'Low')
    match_bar_width : int  -> clamped int 0-100 (for progress bar width attribute)
    eligibility_icon: bool -> CSS class         ('elig-pass'|'elig-fail')
    paise_to_rupees : int  -> int               (amount_paise / 100)
"""

from django import template

register = template.Library()


# ── Match score colour (used as CSS modifier class) ───────────────────────────

@register.filter(name="match_color")
def match_color(score):
    """
    Returns a theme-consistent CSS class suffix based on the match score.

    Usage:  <div class="match-badge match-{{ scholarship.match_score|match_color }}">
    """
    try:
        score = int(score)
    except (TypeError, ValueError):
        return "muted"
    if score >= 80:
        return "green"
    if score >= 60:
        return "yellow"
    if score >= 40:
        return "orange"
    return "red"


# ── Match score human label ────────────────────────────────────────────────────

@register.filter(name="match_label")
def match_label(score):
    """
    Returns a human-readable label for the match score.

    Usage:  {{ scholarship.match_score|match_label }}
    """
    try:
        score = int(score)
    except (TypeError, ValueError):
        return "Unknown"
    if score >= 80:
        return "Excellent Match"
    if score >= 60:
        return "Good Match"
    if score >= 40:
        return "Partial Match"
    return "Low Match"


# ── Progress bar width (clamped 0-100) ────────────────────────────────────────

@register.filter(name="match_bar_width")
def match_bar_width(score):
    """
    Clamps the score to [0, 100] for safe use in style="width: X%".

    Usage:  <div class="bar-fill" style="width:{{ score|match_bar_width }}%;"></div>
    """
    try:
        return max(0, min(100, int(score)))
    except (TypeError, ValueError):
        return 0


# ── Eligibility check icon CSS class ─────────────────────────────────────────

@register.filter(name="eligibility_icon")
def eligibility_icon(passed):
    """
    Returns CSS class for the eligibility tracker row icon.

    Usage:  <span class="elig-icon {{ criterion.passed|eligibility_icon }}"></span>
    """
    return "elig-pass" if passed else "elig-fail"


# ── Paise to rupees ───────────────────────────────────────────────────────────

@register.filter(name="paise_to_rupees")
def paise_to_rupees(paise):
    """
    Converts Razorpay paise amount to rupees (integer).

    Usage:  Rs.{{ funding.amount_paise|paise_to_rupees }}
    """
    try:
        return int(paise) // 100
    except (TypeError, ValueError):
        return 0
