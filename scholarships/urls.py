from django.urls import path
from . import views

app_name = 'scholarships'

urlpatterns = [
    path('', views.scholarship_list, name='scholarship_list'),
    path('recommended/', views.recommended_scholarships, name='recommended'),
    path('<int:pk>/', views.scholarship_detail, name='scholarship_detail'),
]
