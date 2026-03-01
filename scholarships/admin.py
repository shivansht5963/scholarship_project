from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Scholarship, EligibilityCriteria, RequiredDocument, ScholarshipFunding,
    MarksheetVerification, FeesVerification, ScholarshipAward,
    ScholarshipCertificate,
)


class RequiredDocumentInline(admin.TabularInline):
    model = RequiredDocument
    extra = 2
    fields = ['document_name', 'description', 'is_mandatory', 'verification_strictness']


class EligibilityCriteriaInline(admin.TabularInline):
    model = EligibilityCriteria
    extra = 2
    fields = ['criterion_type', 'comparison_operator', 'value', 'is_required']


class ScholarshipFundingInline(admin.StackedInline):
    model = ScholarshipFunding
    extra = 0
    readonly_fields = ['razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'amount_paise', 'created_at', 'paid_at']
    fields = ['status', 'amount_paise', 'razorpay_order_id', 'razorpay_payment_id', 'created_at', 'paid_at']


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ['title', 'org_profile', 'organization', 'deadline', 'total_budget', 'is_active', 'is_funded', 'applications_closed']
    list_filter  = ['is_active', 'is_funded', 'applications_closed', 'education_level', 'distribution_type', 'disbursement_method']
    search_fields = ['title', 'organization', 'description', 'details']
    readonly_fields = ['created_at', 'last_updated']
    date_hierarchy = 'deadline'
    inlines = [ScholarshipFundingInline, RequiredDocumentInline, EligibilityCriteriaInline]

    fieldsets = (
        ('Basics', {
            'fields': ('title', 'org_profile', 'organization', 'logo', 'description', 'deadline')
        }),
        ('Eligibility', {
            'fields': ('education_level', 'courses', 'max_family_income', 'min_percentage', 'demographic_focus')
        }),
        ('Financials', {
            'fields': ('total_budget', 'distribution_type', 'fixed_amount', 'num_winners', 'disbursement_method')
        }),
        ('Platform Filters', {
            'fields': ('min_karma', 'verification_strictness', 'essay_question')
        }),
        ('Legacy Fields', {
            'classes': ('collapse',),
            'fields': ('source_url', 'award_amount', 'details', 'found_by_student', 'finder_karma_awarded')
        }),
        ('Status', {
            'fields': ('is_active', 'is_funded', 'is_verified', 'applications_closed', 'closed_at', 'created_at', 'last_updated')
        }),
    )


@admin.register(EligibilityCriteria)
class EligibilityCriteriaAdmin(admin.ModelAdmin):
    list_display  = ['scholarship', 'criterion_type', 'comparison_operator', 'value', 'is_required']
    list_filter   = ['comparison_operator', 'is_required', 'criterion_type']
    search_fields = ['scholarship__title', 'criterion_type', 'value']


@admin.register(RequiredDocument)
class RequiredDocumentAdmin(admin.ModelAdmin):
    list_display  = ['scholarship', 'document_name', 'is_mandatory', 'verification_strictness']
    list_filter   = ['is_mandatory', 'verification_strictness']
    search_fields = ['scholarship__title', 'document_name', 'description']


@admin.register(ScholarshipFunding)
class ScholarshipFundingAdmin(admin.ModelAdmin):
    list_display  = ['scholarship', 'status', 'amount_paise', 'razorpay_order_id', 'created_at', 'paid_at']
    list_filter   = ['status']
    search_fields = ['scholarship__title', 'razorpay_order_id', 'razorpay_payment_id']
    readonly_fields = ['created_at', 'paid_at']


@admin.register(MarksheetVerification)
class MarksheetVerificationAdmin(admin.ModelAdmin):
    list_display   = ['student', 'last_sem_marks', 'extracted_institution', 'gemini_verified', 'uploaded_at']
    list_filter    = ['gemini_verified']
    search_fields  = ['student__full_name', 'extracted_institution', 'extracted_student_name']
    readonly_fields = ['uploaded_at', 'verified_at', 'raw_gemini_response']


@admin.register(FeesVerification)
class FeesVerificationAdmin(admin.ModelAdmin):
    list_display   = ['student', 'total_annual_fees', 'extracted_college_name', 'college_match', 'gemini_verified', 'uploaded_at']
    list_filter    = ['gemini_verified', 'college_match']
    search_fields  = ['student__full_name', 'extracted_college_name', 'extracted_student_name']
    readonly_fields = ['uploaded_at', 'verified_at', 'raw_gemini_response']


@admin.register(ScholarshipAward)
class ScholarshipAwardAdmin(admin.ModelAdmin):
    list_display   = ['merit_rank', 'student', 'scholarship', 'amount_awarded', 'merit_score', 'transfer_status', 'awarded_at']
    list_filter    = ['transfer_status', 'scholarship']
    search_fields  = ['student__full_name', 'scholarship__title', 'razorpay_payout_id', 'transfer_ref']
    readonly_fields = ['awarded_at', 'transfer_initiated_at', 'transfer_completed_at']
    ordering       = ['scholarship', 'merit_rank']


@admin.register(ScholarshipCertificate)
class ScholarshipCertificateAdmin(admin.ModelAdmin):
    list_display  = ['certificate_id', 'student_name', 'scholarship_name', 'issued_at', 'is_valid', 'cert_preview']
    list_filter   = ['is_valid', 'issued_at']
    search_fields = ['certificate_id', 'award__student__full_name', 'award__scholarship__title']
    readonly_fields = ['certificate_id', 'issued_at', 'cert_preview', 'qr_preview']
    fields = ['certificate_id', 'award', 'issued_at', 'is_valid', 'certificate_image', 'cert_preview', 'qr_code', 'qr_preview']

    @admin.display(description='Student')
    def student_name(self, obj):
        return obj.award.student.full_name

    @admin.display(description='Scholarship')
    def scholarship_name(self, obj):
        return obj.award.scholarship.title

    @admin.display(description='Certificate Preview')
    def cert_preview(self, obj):
        if obj.certificate_image:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="height:80px;border:1px solid #ccc;border-radius:4px"/>'
                '</a>', obj.certificate_image.url, obj.certificate_image.url
            )
        return '—'

    @admin.display(description='QR Code')
    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" style="height:80px"/>', obj.qr_code.url
            )
        return '—'


