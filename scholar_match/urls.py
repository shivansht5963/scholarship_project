"""
URL configuration for scholar_match project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls')), 
    path('scholarships/', include('scholarships.urls')),  # Uncommented
    path('applications/', include('applications.urls')),  # Uncommented
    path('karma/', include('karma.urls')),  # Karma system
    
    # Moderator panel
    path('moderator/', include('moderator_panel.urls')), 
    path('organization/', include('funder_portal.urls')),
]

# Serve media files always — required for public document access on Render
# (For hackathon: fine to serve via Django/gunicorn directly)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
