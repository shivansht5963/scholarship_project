from django.contrib import admin
from .models import Application, UploadedDocument, ApplicationRoadmapStep

admin.site.register(Application)
admin.site.register(UploadedDocument)
admin.site.register(ApplicationRoadmapStep)