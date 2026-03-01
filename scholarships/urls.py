from django.urls import path
from . import views

app_name = 'scholarships'

urlpatterns = [
    path('', views.scholarship_list, name='scholarship_list'),
    path('recommended/', views.recommended_scholarships, name='recommended'),
    path('external/', views.external_scholarships, name='external_scholarships'),
    path('<int:pk>/', views.scholarship_detail, name='scholarship_detail'),
    # Public certificate verification — no login required
    path('certificates/verify/<uuid:cert_uuid>/', views.verify_certificate, name='verify_certificate'),
]

