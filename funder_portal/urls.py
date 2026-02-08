# funder_portal/urls.py

from django.urls import path
from . import views

app_name = 'funder_portal'

urlpatterns = [
    path('dashboard/', views.organization_dashboard, name='funder_dashboard'),
    
    # Scholarship management
    path('scholarship/new/', views.manage_scholarship, name='create_scholarship'),
    path('scholarship/<int:pk>/edit/', views.manage_scholarship, name='edit_scholarship'),
    path('scholarship/<int:pk>/delete/', views.delete_scholarship, name='delete_scholarship'),
    
    # Application review
    path('applications/', views.view_applications, name='view_applications'),
    path('applications/<int:pk>/', views.application_detail, name='application_detail'),
    path('applications/<int:pk>/decision/', views.make_decision, name='make_decision'),
]