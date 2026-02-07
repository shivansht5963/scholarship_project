from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.moderator_dashboard, name = 'moderator_dashboard'),
    path('scholarships/add/', views.add_scholarship, name='moderator_add_scholarship'),
]