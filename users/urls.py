# users/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import otr_views

urlpatterns = [
    # Login / Logout
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Dashboard redirect based on role
    path('dashboard/', views.smart_dashboard_redirect, name='dashboard'),

    # Student dashboard
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),

    # OTR (One-Time Registration) Process
    path('otr/', otr_views.otr_welcome, name='otr_welcome'),
    path('otr/step2/', otr_views.otr_step2, name='otr_step2'),
    path('otr/step3/', otr_views.otr_step3, name='otr_step3'),
    path('otr/step4/', otr_views.otr_step4, name='otr_step4'),
    path('otr/step5/', otr_views.otr_step5, name='otr_step5'),
    path('otr/step6/', otr_views.otr_step6, name='otr_step6'),
    path('otr/step7/', otr_views.otr_step7, name='otr_step7'),
]