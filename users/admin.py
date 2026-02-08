from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StudentProfile, AcademicRecord, ModeratorProfile, OrganizationProfile, StudentDocument

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin with role flags and password management"""
    list_display = ['username', 'email', 'is_student', 'is_moderator', 'is_organization', 'is_staff', 'is_active']
    list_filter = ['is_student', 'is_moderator', 'is_organization', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    # Add role fields to the fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role Flags', {
            'fields': ('is_student', 'is_moderator', 'is_organization'),
        }),
    )
    
    # Add role fields to add form
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role Flags', {
            'fields': ('is_student', 'is_moderator', 'is_organization'),
        }),
    )

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'otr_completed', 'profile_completion', 'created_at']
    list_filter = ['otr_completed', 'caste_category', 'is_disabled', 'gender', 'created_at']
    search_fields = ['full_name', 'user__username', 'aadhaar_number', 'phone']
    readonly_fields = ['created_at', 'profile_completion']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'full_name', 'dob', 'gender', 'phone')
        }),
        ('Family Details', {
            'fields': ('father_name', 'mother_name', 'annual_income', 'caste_category', 'is_disabled')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'pin_code')
        }),
        ('Identity & Banking', {
            'fields': ('aadhaar_number', 'bank_account_number', 'bank_ifsc_code', 'bank_name')
        }),
        ('OTR Tracking', {
            'fields': ('otr_completed', 'otr_step', 'profile_completion'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

class AcademicRecordInline(admin.TabularInline):
    model = AcademicRecord
    extra = 1
    fields = ['degree_level', 'stream', 'current_year', 'last_exam_score']

@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'degree_level', 'stream', 'current_year', 'last_exam_score']
    list_filter = ['degree_level', 'current_year']
    search_fields = ['student__full_name', 'institution_name', 'stream']

@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ['student', 'document_type', 'is_verified', 'uploaded_at']
    list_filter = ['document_type', 'is_verified', 'uploaded_at']
    search_fields = ['student__full_name', 'student__user__username']
    readonly_fields = ['uploaded_at']
    
    fieldsets = (
        ('Document Information', {
            'fields': ('student', 'document_type', 'file')
        }),
        ('Verification', {
            'fields': ('is_verified', 'notes')
        }),
        ('Timestamp', {
            'fields': ('uploaded_at',)
        }),
    )

@admin.register(ModeratorProfile)
class ModeratorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization_name', 'contact_phone', 'is_verified']
    list_filter = ['is_verified']
    search_fields = ['user__username', 'organization_name', 'contact_phone']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Organization Details', {
            'fields': ('organization_name', 'contact_phone')
        }),
        ('Verification', {
            'fields': ('is_verified',)
        }),
    )

@admin.register(OrganizationProfile)
class OrganizationProfileAdmin(admin.ModelAdmin):
    list_display = ['organization_name', 'contact_person', 'official_email', 'is_verified_funder']
    list_filter = ['is_verified_funder']
    search_fields = ['organization_name', 'official_email', 'contact_person']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Organization Details', {
            'fields': ('organization_name', 'contact_person', 'official_email', 'website_url')
        }),
        ('Verification', {
            'fields': ('is_verified_funder',)
        }),
    )
