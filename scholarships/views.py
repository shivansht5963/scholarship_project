from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Scholarship

@login_required
def scholarship_list(request):
    """Display all active scholarships with search and filtering"""
    
    # Start with all active scholarships
    scholarships = Scholarship.objects.filter(is_active=True).order_by('-deadline')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        scholarships = scholarships.filter(
            Q(name__icontains=search_query) |
            Q(organization__icontains=search_query) |
            Q(details__icontains=search_query)
        )
    
    # Filter by organization
    org_filter = request.GET.get('organization', '')
    if org_filter:
        scholarships = scholarships.filter(organization__icontains=org_filter)
    
    # Filter by amount range
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    if min_amount:
        scholarships = scholarships.filter(award_amount__gte=min_amount)
    if max_amount:
        scholarships = scholarships.filter(award_amount__lte=max_amount)
    
    # Filter by deadline (upcoming deadlines)
    deadline_filter = request.GET.get('deadline', '')
    today = datetime.now().date()
    if deadline_filter == 'week':
        scholarships = scholarships.filter(deadline__gte=today, deadline__lte=today + timedelta(days=7))
    elif deadline_filter == 'month':
        scholarships = scholarships.filter(deadline__gte=today, deadline__lte=today + timedelta(days=30))
    elif deadline_filter == 'quarter':
        scholarships = scholarships.filter(deadline__gte=today, deadline__lte=today + timedelta(days=90))
    
    # Sorting
    sort_by = request.GET.get('sort', '-deadline')
    valid_sorts = ['deadline', '-deadline', 'award_amount', '-award_amount', 'name']
    if sort_by in valid_sorts:
        scholarships = scholarships.order_by(sort_by)
    
    # Get unique organizations for filter dropdown
    organizations = Scholarship.objects.filter(is_active=True).values_list('organization', flat=True).distinct()
    
    context = {
        'scholarships': scholarships,
        'organizations': organizations,
        'total_count': scholarships.count(),
        'search_query': search_query,
        'org_filter': org_filter,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'deadline_filter': deadline_filter,
        'sort_by': sort_by,
    }
    
    return render(request, 'scholarships/scholarship_list.html', context)

@login_required
def scholarship_detail(request, pk):
    """Display detailed information about a specific scholarship"""
    scholarship = get_object_or_404(Scholarship, pk=pk, is_active=True)
    
    # Get related scholarships (same organization only, since award_amount is a CharField)
    related_scholarships = Scholarship.objects.filter(
        is_active=True,
        organization=scholarship.organization
    ).exclude(pk=pk).order_by('-deadline')[:3]
    
    context = {
        'scholarship': scholarship,
        'related_scholarships': related_scholarships,
    }
    
    return render(request, 'scholarships/scholarship_detail.html', context)

@login_required
def recommended_scholarships(request):
    """Placeholder for AI-recommended scholarships based on student profile"""
    # This will be enhanced in future phases with actual recommendation logic
    scholarships = Scholarship.objects.filter(is_active=True).order_by('-deadline')[:6]
    
    context = {
        'scholarships': scholarships,
        'message': 'Showing popular scholarships. Personalized recommendations coming soon!'
    }
    
    return render(request, 'scholarships/recommended.html', context)

