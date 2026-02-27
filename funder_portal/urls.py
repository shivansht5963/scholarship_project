# funder_portal/urls.py

from django.urls import path
from . import views

app_name = 'funder_portal'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.organization_dashboard, name='funder_dashboard'),

    # ── Multi-step scholarship creation wizard ────────────────────────────
    path('scholarship/new/',                    views.create_step1,        name='create_scholarship'),
    path('scholarship/new/step1/',              views.create_step1,        name='create_step1'),
    path('scholarship/new/step2/<int:draft_id>/', views.create_step2,     name='create_step2'),
    path('scholarship/new/step3/<int:draft_id>/', views.create_step3,     name='create_step3'),
    path('scholarship/new/step4/<int:draft_id>/', views.create_step4,     name='create_step4'),
    path('scholarship/review/<int:draft_id>/',  views.scholarship_review,  name='scholarship_review'),

    # ── Razorpay ─────────────────────────────────────────────────────────
    path('scholarship/pay/<int:draft_id>/',     views.initiate_payment,    name='initiate_payment'),
    path('payment/callback/',                   views.payment_callback,    name='payment_callback'),

    # ── Legacy edit / delete ──────────────────────────────────────────────
    path('scholarship/<int:pk>/edit/',          views.manage_scholarship,  name='edit_scholarship'),
    path('scholarship/<int:pk>/delete/',        views.delete_scholarship,  name='delete_scholarship'),

    # ── Application review ────────────────────────────────────────────────
    path('applications/',                       views.view_applications,   name='view_applications'),
    path('applications/<int:pk>/',              views.application_detail,  name='application_detail'),
    path('applications/<int:pk>/decision/',     views.make_decision,       name='make_decision'),
]