from django.contrib import admin
from .models import KarmaTransaction, ScholarshipSubmission, KarmaReward, RedemptionHistory


@admin.register(KarmaTransaction)
class KarmaTransactionAdmin(admin.ModelAdmin):
    list_display = ['student', 'points', 'transaction_type', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['student__full_name', 'description']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        # Transactions should only be created programmatically
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Audit log - should not be deletable
        return False


@admin.register(ScholarshipSubmission)
class ScholarshipSubmissionAdmin(admin.ModelAdmin):
    list_display = ['scholarship_name', 'submitted_by', 'status', 'karma_awarded', 'submitted_at']
    list_filter = ['status', 'submitted_at', 'reviewed_at']
    search_fields = ['scholarship_name', 'organization', 'submitted_by__full_name']
    readonly_fields = ['submitted_at', 'reviewed_at']
    date_hierarchy = 'submitted_at'
    fieldsets = (
        ('Submission Details', {
            'fields': ('submitted_by', 'scholarship_name', 'organization', 'website_url', 'proof_document')
        }),
        ('Review Status', {
            'fields': ('status', 'karma_awarded', 'admin_notes', 'reviewed_by', 'reviewed_at')
        }),
        ('Metadata', {
            'fields': ('submitted_at',)
        }),
    )


@admin.register(KarmaReward)
class KarmaRewardAdmin(admin.ModelAdmin):
    list_display = ['reward_name', 'reward_type', 'karma_cost', 'stock_quantity', 'is_active', 'created_at']
    list_filter = ['reward_type', 'is_active', 'created_at']
    search_fields = ['reward_name', 'description']
    readonly_fields = ['created_at']
    list_editable = ['is_active']


@admin.register(RedemptionHistory)
class RedemptionHistoryAdmin(admin.ModelAdmin):
    list_display = ['student', 'reward', 'karma_spent', 'redemption_code', 'redeemed_at']
    list_filter = ['redeemed_at', 'reward__reward_type']
    search_fields = ['student__full_name', 'redemption_code', 'reward__reward_name']
    readonly_fields = ['student', 'reward', 'karma_spent', 'redemption_code', 'redeemed_at']
    date_hierarchy = 'redeemed_at'
    
    def has_add_permission(self, request):
        # Redemptions should only be created through the frontend
        return False
