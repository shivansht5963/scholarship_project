from django.contrib import admin
from .models import Scholarship, EligibilityCriteria, RequiredDocument

class RequiredDocumentInline(admin.TabularInline):
    model = RequiredDocument
    extra = 2
    fields = ['document_name', 'description', 'is_mandatory']

class EligibilityCriteriaInline(admin.TabularInline):
    model = EligibilityCriteria
    extra = 2
    fields = ['criterion_type', 'comparison_operator', 'value', 'is_required']

@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'deadline', 'award_amount', 'is_active', 'is_verified', 'last_updated']
    list_filter = ['is_active', 'is_verified', 'deadline']
    search_fields = ['name', 'organization', 'details']
    readonly_fields = ['last_updated']
    date_hierarchy = 'deadline'
    inlines = [RequiredDocumentInline, EligibilityCriteriaInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'organization', 'source_url')
        }),
        ('Scholarship Details', {
            'fields': ('award_amount', 'deadline', 'details')
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified', 'last_updated')
        }),
    )

@admin.register(EligibilityCriteria)
class EligibilityCriteriaAdmin(admin.ModelAdmin):
    list_display = ['scholarship', 'criterion_type', 'comparison_operator', 'value', 'is_required']
    list_filter = ['comparison_operator', 'is_required', 'criterion_type']
    search_fields = ['scholarship__name', 'criterion_type', 'value']

@admin.register(RequiredDocument)
class RequiredDocumentAdmin(admin.ModelAdmin):
    list_display = ['scholarship', 'document_name', 'is_mandatory']
    list_filter = ['is_mandatory']
    search_fields = ['scholarship__name', 'document_name', 'description']