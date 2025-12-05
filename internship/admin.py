from django.contrib import admin
from .models import Company, Internship, Application, CompanyReview

class CompanyAdmin(admin.ModelAdmin):
    """Admin for Company model."""
    list_display = ('name', 'city', 'province', 'status', 'has_incentives', 'get_active_internships_count')
    list_filter = ('status', 'has_incentives', 'city', 'province')
    search_fields = ('name', 'description', 'street', 'barangay', 'city', 'province')
    
    def get_active_internships_count(self, obj):
        return obj.get_active_internships_count()
    get_active_internships_count.short_description = 'Active Internships'

class InternshipAdmin(admin.ModelAdmin):
    """Admin for Internship model."""
    list_display = ('title', 'company', 'is_active', 'slots_available', 'created_at')
    list_filter = ('is_active', 'company', 'created_at')
    search_fields = ('title', 'description', 'company__name')
    filter_horizontal = ('recommended_courses', 'required_skills')

class ApplicationAdmin(admin.ModelAdmin):
    """Admin for Application model."""
    list_display = ('student', 'internship', 'status', 'match_score', 'applied_at', 'email_sent')
    list_filter = ('status', 'applied_at', 'email_sent')
    search_fields = ('student__user__username', 'student__user__first_name', 'student__user__last_name', 'internship__title', 'internship__company__name')
    readonly_fields = ('match_score', 'applied_at')

class CompanyReviewAdmin(admin.ModelAdmin):
    """Admin for CompanyReview model."""
    list_display = ('company', 'get_student', 'rating', 'is_anonymous', 'created_at')
    list_filter = ('rating', 'is_anonymous', 'created_at')
    search_fields = ('company__name', 'student__user__username', 'comment')
    
    def get_student(self, obj):
        if obj.is_anonymous:
            return 'Anonymous'
        return obj.student.user.username
    get_student.short_description = 'Student'

# Register models
admin.site.register(Company, CompanyAdmin)
admin.site.register(Internship, InternshipAdmin)
admin.site.register(Application, ApplicationAdmin)
admin.site.register(CompanyReview, CompanyReviewAdmin)
