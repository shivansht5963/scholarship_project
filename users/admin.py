from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# Import the new OrganizationProfile model
from .models import User, StudentProfile, AcademicRecord, ModeratorProfile, OrganizationProfile 

# Register the custom User model (inherits basic functionality)
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    # 1. ADD 'is_organization' to list_display
    list_display = ('username', 'email', 'is_student', 'is_moderator', 'is_organization', 'is_staff') 

    # 2. UPDATE fieldsets to allow editing 'is_organization'
    # BaseUserAdmin already defines a 'fieldsets' tuple. We extend the 'Permissions' section.
    fieldsets = list(BaseUserAdmin.fieldsets)
    # Find the 'Permissions' fieldset index (usually 2) and update its fields
    permissions_fieldset_index = 2
    
    # Check if the structure exists before modifying (safe way)
    if len(fieldsets) > permissions_fieldset_index and fieldsets[permissions_fieldset_index][0] == 'Permissions':
        # Convert tuple to list, add the new field
        current_fields = list(fieldsets[permissions_fieldset_index][1]['fields'])
        current_fields.insert(0, 'is_organization') # Insert near the other role fields
        fieldsets[permissions_fieldset_index][1]['fields'] = tuple(current_fields)
    
    # If you can't access the index easily, use the simplest manual override (less maintainable but simple):
    # fieldsets = BaseUserAdmin.fieldsets + (
    #     ('Role Status', {'fields': ('is_student', 'is_moderator', 'is_organization')}),
    # )


# Register the remaining core profile models
admin.site.register(StudentProfile)
admin.site.register(AcademicRecord)
admin.site.register(ModeratorProfile)
# 3. REGISTER THE NEW MODEL
admin.site.register(OrganizationProfile)