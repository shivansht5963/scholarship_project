from django.contrib import admin
from .models import AICheckLog

@admin.register(AICheckLog)
class AICheckLogAdmin(admin.ModelAdmin):
    list_display = ['application', 'check_type', 'is_success', 'timestamp']
    list_filter = ['check_type', 'is_success', 'timestamp']
    search_fields = ['application__student__full_name', 'api_response']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('AI Check Information', {
            'fields': ('application', 'check_type', 'is_success')
        }),
        ('API Response', {
            'fields': ('api_response',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )