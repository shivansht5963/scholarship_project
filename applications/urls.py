from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # Student application workflow
    path('apply/<int:scholarship_pk>/', views.create_application, name='create_application'),
    path('<int:pk>/upload/', views.upload_documents, name='upload_documents'),
    path('<int:pk>/review/', views.review_application, name='review_application'),
    path('<int:pk>/submit/', views.submit_application, name='submit_application'),
    
    # Student dashboard
    path('my-applications/', views.my_applications, name='my_applications'),
    path('<int:pk>/status/', views.application_status, name='application_status'),
]
