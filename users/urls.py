# users/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views # Import Django's built-in views
from . import views # Your custom views (like student_dashboard)

urlpatterns = [
    # 1. AUTHENTICATION VIEWS (Built-in)
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/accounts/login/'), name='logout'),

    # 2. DASHBOARD VIEWS (Your custom views)
    # We must create this placeholder view since LOGIN_REDIRECT_URL uses it.
    path('dashboard/', views.smart_dashboard_redirect, name='smart_dashboard_redirect'),
    # ... (other user-related paths)
]