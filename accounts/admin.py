from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Course, Skill, StudentProfile, 
    RequiredDocument, StudentDocument, 
    AdviserProfile, CoordinatorProfile
)

class CustomUserAdmin(UserAdmin):
    """Custom admin for User model."""
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    list_filter = ('user_type', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('User type', {'fields': ('user_type',)}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type'),
        }),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

class StudentProfileAdmin(admin.ModelAdmin):
    """Admin for StudentProfile model."""
    list_display = ('user', 'get_full_name', 'course', 'year_level', 'section', 'ojt_status')
    list_filter = ('course', 'year_level', 'ojt_status')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'section')
    filter_horizontal = ('skills',)
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Name'

class StudentDocumentAdmin(admin.ModelAdmin):
    """Admin for StudentDocument model."""
    list_display = ('student', 'document_type', 'filename', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('student__user__username', 'document_type__name')

class AdviserProfileAdmin(admin.ModelAdmin):
    """Admin for AdviserProfile model."""
    list_display = ('user', 'department', 'get_courses', 'sections')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'department')
    filter_horizontal = ('courses',)
    
    def get_courses(self, obj):
        return ", ".join([c.code for c in obj.courses.all()])
    get_courses.short_description = 'Courses'

class CoordinatorProfileAdmin(admin.ModelAdmin):
    """Admin for CoordinatorProfile model."""
    list_display = ('user', 'department')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'department')

# Register models
admin.site.register(User, CustomUserAdmin)
admin.site.register(Course)
admin.site.register(Skill)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(RequiredDocument)
admin.site.register(StudentDocument, StudentDocumentAdmin)
admin.site.register(AdviserProfile, AdviserProfileAdmin)
admin.site.register(CoordinatorProfile, CoordinatorProfileAdmin)
