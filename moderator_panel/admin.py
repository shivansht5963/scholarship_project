from django.contrib import admin
from .models import ModeratorActivityLog, TaskAssignment

admin.site.register(ModeratorActivityLog)
admin.site.register(TaskAssignment)