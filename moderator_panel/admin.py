from django.contrib import admin
from .models import ModeratorActivityLog, TaskAssignment

@admin.register(ModeratorActivityLog)
class ModeratorActivityLogAdmin(admin.ModelAdmin):
    list_display = ['moderator', 'action_type', 'target_application', 'timestamp']
    list_filter = ['action_type', 'timestamp']
    search_fields = ['moderator__user__username', 'details']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('moderator', 'action_type', 'target_application')
        }),
        ('Details', {
            'fields': ('details',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )

@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ['moderator', 'application', 'assignment_date', 'due_date', 'is_complete']
    list_filter = ['is_complete', 'assignment_date', 'due_date']
    search_fields = ['moderator__user__username', 'application__student__full_name']
    readonly_fields = ['assignment_date']
    date_hierarchy = 'assignment_date'
    
    fieldsets = (
        ('Assignment Information', {
            'fields': ('moderator', 'application')
        }),
        ('Dates', {
            'fields': ('assignment_date', 'due_date')
        }),
        ('Status', {
            'fields': ('is_complete',)
        }),
    )