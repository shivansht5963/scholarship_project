"""
scholarships/pin_classifier.py

Offline city/district tier classifier for scholarship eligibility.

Usage:
    from scholarships.pin_classifier import classify_location

    result = classify_location(city="Agra", state="Uttar Pradesh")
    # -> {'is_rural': False, 'is_tier2': True, 'is_tier1': False,
    #     'city': 'agra', 'state': 'uttar pradesh'}

Classification tiers (Government of India definition):
    Tier-1  : 8 major metros — Delhi, Mumbai, Bengaluru, Hyderabad,
              Chennai, Kolkata, Pune, Ahmedabad
    Tier-2  : Government Category B cities + key state capitals (~100+ cities)
    Rural   : Everything else (default)

Notes:
    - Lookup is case-insensitive.
    - Falls back gracefully when city is blank/unknown.
    - No external API, no CSV file, no internet required at runtime.
"""

from __future__ import annotations
from .data.districts import TIER1_DISTRICTS, TIER2_DISTRICTS


def classify_location(
    city: str = "",
    state: str = "",
    pin_code: str = "",
) -> dict:
    """
    Classify a student's location into Tier-1, Tier-2, or Rural.

    Parameters
    ----------
    city     : StudentProfile.city
    state    : StudentProfile.state
    pin_code : StudentProfile.pin_code  (reserved for future CSV lookup)

    Returns
    -------
    dict with keys:
        is_tier1  (bool)
        is_tier2  (bool)
        is_rural  (bool)   — True when not tier1 and not tier2
        city      (str)    — normalised lowercase city name
        state     (str)    — normalised lowercase state name
    """
    city_norm  = (city or "").strip().lower()
    state_norm = (state or "").strip().lower()

    # Prefer city lookup; fallback to state for state-capitals that share name
    lookup_key = city_norm or state_norm

    is_tier1 = lookup_key in TIER1_DISTRICTS
    is_tier2 = (not is_tier1) and (lookup_key in TIER2_DISTRICTS)
    is_rural = not is_tier1 and not is_tier2

    return {
        "is_tier1": is_tier1,
        "is_tier2": is_tier2,
        "is_rural": is_rural,
        "city":     city_norm,
        "state":    state_norm,
    }


def student_location_tags(student_profile) -> set[str]:
    """
    Return the set of demographic location tags for a StudentProfile.

    These tags are matched against Scholarship.demographic_focus list.

    Example return values: {"rural"}, {"tier2"}, {"tier2", "rural"}, set()

    Parameters
    ----------
    student_profile : users.models.StudentProfile instance
    """
    result = classify_location(
        city=getattr(student_profile, "city", ""),
        state=getattr(student_profile, "state", ""),
        pin_code=getattr(student_profile, "pin_code", ""),
    )

    tags: set[str] = set()
    if result["is_rural"]:
        tags.add("rural")
    if result["is_tier2"]:
        tags.add("tier2")
    return tags
