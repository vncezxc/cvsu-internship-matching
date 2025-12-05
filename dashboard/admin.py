from django.contrib import admin
from .models import DashboardStatistics, Report

class DashboardStatisticsAdmin(admin.ModelAdmin):
    """Admin for DashboardStatistics model."""
    list_display = (
        'date', 'total_students', 'students_ongoing', 
        'total_companies', 'active_companies',
        'total_internships', 'total_applications'
    )
    list_filter = ('date',)
    readonly_fields = (
        'date', 'total_students', 'students_looking', 'students_waiting', 
        'students_ongoing', 'students_completed', 'total_companies', 
        'active_companies', 'total_internships', 'active_internships',
        'total_applications', 'pending_applications', 'accepted_applications',
        'rejected_applications'
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

class ReportAdmin(admin.ModelAdmin):
    """Admin for Report model."""
    list_display = ('get_report_type_display', 'generated_by', 'generated_at')
    list_filter = ('report_type', 'generated_at')
    search_fields = ('generated_by__username', 'report_type')
    readonly_fields = ('generated_by', 'generated_at', 'report_type')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

# Register models
admin.site.register(DashboardStatistics, DashboardStatisticsAdmin)
admin.site.register(Report, ReportAdmin)
