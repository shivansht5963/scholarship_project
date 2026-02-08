"""URL configuration for karma app."""
from django.urls import path
from . import views

app_name = 'karma'

urlpatterns = [
    # Student URLs
    path('dashboard/', views.karma_dashboard, name='karma_dashboard'),
    path('submit-scholarship/', views.submit_scholarship, name='submit_scholarship'),
    path('leaderboard/', views.karma_leaderboard, name='leaderboard'),
    path('store/', views.karma_store, name='karma_store'),
    path('redeem/<int:reward_id>/', views.redeem_reward, name='redeem_reward'),
    
    # Moderator URLs
    path('moderator/overview/', views.moderator_karma_overview, name='moderator_overview'),
    path('moderator/verify/<int:submission_id>/', views.verify_submission, name='verify_submission'),
]
