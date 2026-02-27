from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Scholarship, RequiredDocument


@login_required
def scholarship_list(request):
    """Display all active scholarships with search and filtering."""
    scholarships = Scholarship.objects.filter(is_active=True).select_related('org_profile')

    # Search — title, description, org name
    search_query = request.GET.get('search', '')
    if search_query:
        scholarships = scholarships.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(organization__icontains=search_query)
        )

    # Filter by organization (legacy CharField or org_profile name)
    org_filter = request.GET.get('organization', '')
    if org_filter:
        scholarships = scholarships.filter(
            Q(organization__icontains=org_filter) |
            Q(org_profile__organization_name__icontains=org_filter)
        )

    # Filter by education level (new field)
    edu_filter = request.GET.get('education', '')
    if edu_filter:
        scholarships = scholarships.filter(education_level=edu_filter)

    # Filter by deadline window
    deadline_filter = request.GET.get('deadline', '')
    today = datetime.now().date()
    if deadline_filter == 'week':
        scholarships = scholarships.filter(deadline__gte=today, deadline__lte=today + timedelta(days=7))
    elif deadline_filter == 'month':
        scholarships = scholarships.filter(deadline__gte=today, deadline__lte=today + timedelta(days=30))
    elif deadline_filter == 'quarter':
        scholarships = scholarships.filter(deadline__gte=today, deadline__lte=today + timedelta(days=90))

    # Sorting — new fields
    sort_by = request.GET.get('sort', '-created_at')
    valid_sorts = ['deadline', '-deadline', 'title', '-title', 'total_budget', '-total_budget', 'created_at', '-created_at']
    if sort_by in valid_sorts:
        scholarships = scholarships.order_by(sort_by)
    else:
        scholarships = scholarships.order_by('-created_at')

    # Distinct org names for sidebar dropdown
    organizations = (
        Scholarship.objects
        .filter(is_active=True)
        .values_list('organization', flat=True)
        .distinct()
    )

    # Education level choices for new filter
    edu_choices = Scholarship.EDUCATION_LEVEL_CHOICES if hasattr(Scholarship, 'EDUCATION_LEVEL_CHOICES') else []

    context = {
        'scholarships': scholarships,
        'organizations': organizations,
        'edu_choices': edu_choices,
        'total_count': scholarships.count(),
        'search_query': search_query,
        'org_filter': org_filter,
        'edu_filter': edu_filter,
        'deadline_filter': deadline_filter,
        'sort_by': sort_by,
    }
    return render(request, 'scholarships/scholarship_list.html', context)


@login_required
def scholarship_detail(request, pk):
    """Display detailed information about a specific scholarship."""
    scholarship = get_object_or_404(Scholarship, pk=pk, is_active=True)

    # Required documents for this scholarship
    required_docs = RequiredDocument.objects.filter(scholarship=scholarship)

    # Related scholarships — same education level or same org
    related = Scholarship.objects.filter(
        is_active=True,
        education_level=scholarship.education_level,
    ).exclude(pk=pk).select_related('org_profile').order_by('-created_at')[:3]

    if not related.exists():
        related = Scholarship.objects.filter(
            is_active=True,
        ).exclude(pk=pk).order_by('-created_at')[:3]

    context = {
        'scholarship': scholarship,
        'required_docs': required_docs,
        'related_scholarships': related,
    }
    return render(request, 'scholarships/scholarship_detail.html', context)


@login_required
def recommended_scholarships(request):
    """Placeholder for AI-recommended scholarships."""
    scholarships = Scholarship.objects.filter(is_active=True).order_by('-created_at')[:6]
    context = {
        'scholarships': scholarships,
        'message': 'Showing popular scholarships. Personalized recommendations coming soon!',
    }
    return render(request, 'scholarships/recommended.html', context)
