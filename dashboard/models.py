from django.db import models
from django.utils import timezone
from accounts.models import User, StudentProfile
from internship.models import Company, Internship, Application

class DashboardStatistics(models.Model):
    """Model to store dashboard statistics for quick access."""
    
    date = models.DateField(default=timezone.now, unique=True)
    
    # Student statistics
    total_students = models.PositiveIntegerField(default=0)
    students_looking = models.PositiveIntegerField(default=0)
    students_waiting = models.PositiveIntegerField(default=0)
    students_ongoing = models.PositiveIntegerField(default=0)
    students_completed = models.PositiveIntegerField(default=0)
    
    # Company statistics
    total_companies = models.PositiveIntegerField(default=0)
    active_companies = models.PositiveIntegerField(default=0)
    
    # Internship statistics
    total_internships = models.PositiveIntegerField(default=0)
    active_internships = models.PositiveIntegerField(default=0)
    
    # Application statistics
    total_applications = models.PositiveIntegerField(default=0)
    pending_applications = models.PositiveIntegerField(default=0)
    accepted_applications = models.PositiveIntegerField(default=0)
    rejected_applications = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Statistics for {self.date}"
    
    @classmethod
    def update_statistics(cls):
        """Update statistics for the current date."""
        today = timezone.now().date()
        stats, created = cls.objects.get_or_create(date=today)
        
        # Update student statistics
        stats.total_students = StudentProfile.objects.count()
        stats.students_looking = StudentProfile.objects.filter(ojt_status=StudentProfile.OJTStatus.LOOKING).count()
        stats.students_waiting = StudentProfile.objects.filter(ojt_status=StudentProfile.OJTStatus.WAITING).count()
        stats.students_ongoing = StudentProfile.objects.filter(ojt_status=StudentProfile.OJTStatus.ONGOING).count()
        stats.students_completed = StudentProfile.objects.filter(ojt_status=StudentProfile.OJTStatus.COMPLETED).count()
        
        # Update company statistics
        stats.total_companies = Company.objects.count()
        stats.active_companies = Company.objects.filter(status=Company.Status.ACTIVE).count()
        
        # Update internship statistics
        stats.total_internships = Internship.objects.count()
        stats.active_internships = Internship.objects.filter(is_active=True).count()
        
        # Update application statistics
        stats.total_applications = Application.objects.count()
        stats.pending_applications = Application.objects.filter(status=Application.Status.PENDING).count()
        stats.accepted_applications = Application.objects.filter(status=Application.Status.ACCEPTED).count()
        stats.rejected_applications = Application.objects.filter(status=Application.Status.REJECTED).count()
        
        stats.save()
        return stats

class Report(models.Model):
    def save(self, *args, **kwargs):
        from pdf2image import convert_from_path
        from django.core.files.base import ContentFile
        import os
        super().save(*args, **kwargs)
        # Only generate preview for PDFs and if not already set
        if self.file and self.file.name.lower().endswith('.pdf') and not self.preview_image:
            try:
                # Convert first page of PDF to image
                pdf_path = self.file.path
                images = convert_from_path(pdf_path, first_page=1, last_page=1, fmt='jpeg', size=(300, 400))
                if images:
                    img = images[0]
                    img_io = ContentFile(b'')
                    img.save(img_io, format='JPEG', quality=80)
                    img_name = os.path.splitext(os.path.basename(self.file.name))[0] + '_preview.jpg'
                    self.preview_image.save(img_name, img_io, save=False)
                    super().save(update_fields=['preview_image'])
            except Exception as e:
                # Optionally log error
                pass
    """Model to track generated reports."""
    
    class ReportType(models.TextChoices):
        STUDENT_LIST = 'STUDENT_LIST', 'Student List'
        OJT_TRACKING = 'OJT_TRACKING', 'OJT Tracking Sheet'
        COMPANY_LIST = 'COMPANY_LIST', 'Company List'
        APPLICATION_SUMMARY = 'APPLICATION_SUMMARY', 'Application Summary'
    
    report_type = models.CharField(max_length=50, choices=ReportType.choices)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_reports')
    generated_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='reports/', null=True, blank=True)
    preview_image = models.ImageField(upload_to='report_previews/', null=True, blank=True, help_text='Auto-generated thumbnail for preview')
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
