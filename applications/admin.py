from django.contrib import admin
from .models import Application, UploadedDocument, ApplicationRoadmapStep

class UploadedDocumentInline(admin.TabularInline):
    model = UploadedDocument
    extra = 0
    readonly_fields = ['uploaded_at']
    fields = ['document_type', 'file', 'ai_verification_status', 'moderator_verified', 'uploaded_at']

class ApplicationRoadmapStepInline(admin.TabularInline):
    model = ApplicationRoadmapStep
    extra = 0
    fields = ['step_order', 'step_name', 'instructions', 'is_complete']

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['student', 'scholarship', 'status', 'moderator_assigned', 'last_action_date']
    list_filter = ['status', 'last_action_date']
    search_fields = ['student__full_name', 'scholarship__name']
    readonly_fields = ['last_action_date']
    date_hierarchy = 'last_action_date'
    inlines = [UploadedDocumentInline, ApplicationRoadmapStepInline]
    
    fieldsets = (
        ('Application Information', {
            'fields': ('student', 'scholarship', 'status')
        }),
        ('Assignment', {
            'fields': ('moderator_assigned',)
        }),
        ('External Link', {
            'fields': ('application_link',)
        }),
        ('Timestamps', {
            'fields': ('last_action_date',)
        }),
    )

@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ['application', 'document_type', 'ai_verification_status', 'moderator_verified', 'uploaded_at']
    list_filter = ['ai_verification_status', 'moderator_verified', 'uploaded_at']
    search_fields = ['application__student__full_name', 'document_type__document_name']
    readonly_fields = ['uploaded_at']
    date_hierarchy = 'uploaded_at'
    
    fieldsets = (
        ('Document Information', {
            'fields': ('application', 'document_type', 'file')
        }),
        ('Verification Status', {
            'fields': ('ai_verification_status', 'moderator_verified', 'moderator_notes')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at',)
        }),
    )

@admin.register(ApplicationRoadmapStep)
class ApplicationRoadmapStepAdmin(admin.ModelAdmin):
    list_display = ['application', 'step_order', 'step_name', 'is_complete']
    list_filter = ['is_complete']
    search_fields = ['application__student__full_name', 'step_name']
    ordering = ['application', 'step_order']