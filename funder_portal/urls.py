# funder_portal/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Main Dashboard
    path('dashboard/', views.funder_dashboard, name='funder_dashboard'),
    
    # Create New Scholarship (pk is None)
    path('scholarship/new/', views.manage_scholarship, name='funder_add_scholarship'),
    
    # Edit Existing Scholarship (pk is the ID)
    path('scholarship/edit/<int:pk>/', views.manage_scholarship, name='funder_edit_scholarship'),
    
    # Future paths for Review/Analytics will go here
    # path('applications/', views.application_review_list, name='funder_review_apps'),
]