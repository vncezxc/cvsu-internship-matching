from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from accounts.models import User, StudentProfile, Skill, Course, AdviserProfile

class Company(models.Model):
    """Model for companies offering internships."""
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'

    class ApprovalStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    # Company type (private, government, NGO, etc.)
    class CompanyType(models.TextChoices):
        PRIVATE = 'PRIVATE', 'Private'
        GOVERNMENT = 'GOVERNMENT', 'Government'
        NGO = 'NGO', 'Non-Governmental Organization'
        ACADEMIC = 'ACADEMIC', 'Academic/School'
        OTHER = 'OTHER', 'Other'

    company_type = models.CharField(max_length=20, choices=CompanyType.choices, default=CompanyType.PRIVATE)
    company_email = models.EmailField()
    hr_email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    
    # Address fields
    street = models.CharField(max_length=255)
    barangay = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    
    # Location coordinates for map
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Company status
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    # Adviser review status (for student-submitted companies)
    approval_status = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.APPROVED)
    adviser_remark = models.TextField(blank=True)
    is_red_flag = models.BooleanField(default=False)
    is_partner = models.BooleanField(default=False)
    
    # Company incentives
    has_incentives = models.BooleanField(default=False)
    incentives_details = models.TextField(blank=True)
    
    # Company logo
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    # Company banner image
    banner_image = models.ImageField(upload_to='company_banners/', null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_companies')
    
    # Location link
    location_link = models.URLField(blank=True, null=True, help_text="Google Maps or OpenStreetMap link for easy location access.")
    
    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.title()
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.name
    
    def get_full_address(self):
        return f"{self.street}, {self.barangay}, {self.city}, {self.province}"
    
    def get_active_internships_count(self):
        return self.internships.filter(is_active=True).count()

class Internship(models.Model):
    """Model for internship opportunities."""

    class ApprovalStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='internships')
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Recommended courses and skills
    recommended_courses = models.ManyToManyField(Course, related_name='recommended_internships')
    required_skills = models.ManyToManyField(Skill, related_name='required_by_internships')
    
    # Internship details
    is_active = models.BooleanField(default=True)
    slots_available = models.PositiveIntegerField(default=1)
    approval_status = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.APPROVED)

    # Student-submitted internship fields
    submitted_by = models.ForeignKey(
        StudentProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custom_internship_submissions'
    )
    acceptance_letter = models.FileField(
        upload_to='custom_submissions/acceptance_letters/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])]
    )
    job_description = models.FileField(
        upload_to='custom_submissions/job_descriptions/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])]
    )
    adviser = models.ForeignKey(
        AdviserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_internships'
    )
    adviser_remarks = models.TextField(blank=True)
    is_red_flag = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} at {self.company.name}"
    
    def get_match_score(self, student_profile):
        """Calculate match score between internship and student (0-100)."""
        if not student_profile.course or not student_profile.skills.exists():
            return 0

        from .matching import score_internship

        return score_internship(student_profile, self)["score"]

class Application(models.Model):
    """Model for student applications to internships."""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        COMPLETED = 'COMPLETED', 'Completed'
    
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='applications')
    internship = models.ForeignKey(Internship, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    
    # Application details
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    match_score = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    
    # Email tracking
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('student', 'internship')
    
    def __str__(self):
        return f"{self.student.user.username} - {self.internship.title}"
    
    def save(self, *args, **kwargs):
        # Calculate match score if not provided
        if not self.match_score:
            self.match_score = self.internship.get_match_score(self.student)
        
        # Check if status changed to ACCEPTED
        is_new = self.pk is None
        old_status = None
        if not is_new:
            try:
                old_status = Application.objects.get(pk=self.pk).status
            except Application.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # After save, update student profile if status changed to ACCEPTED
        if self.status == self.Status.ACCEPTED and (is_new or old_status != self.Status.ACCEPTED):
            # Update student's current internship and OJT status
            self.student.current_internship = self
            self.student.ojt_status = StudentProfile.OJTStatus.ONGOING
            self.student.save(update_fields=['current_internship', 'ojt_status'])
        
        # If status changed from ACCEPTED to something else, clear current_internship
        elif old_status == self.Status.ACCEPTED and self.status != self.Status.ACCEPTED:
            if self.student.current_internship == self:
                self.student.current_internship = None
                # Only change status if they don't have another accepted application
                other_accepted = Application.objects.filter(
                    student=self.student, 
                    status=self.Status.ACCEPTED
                ).exclude(pk=self.pk).exists()
                if not other_accepted:
                    self.student.ojt_status = StudentProfile.OJTStatus.LOOKING
                self.student.save(update_fields=['current_internship', 'ojt_status'])

class CompanyReview(models.Model):
    """Model for student reviews of companies."""
    
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='reviews')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('student', 'company')
    
    def __str__(self):
        if self.is_anonymous:
            return f"Anonymous - {self.company.name} - {self.rating} stars"
        return f"{self.student.user.username} - {self.company.name} - {self.rating} stars"


class MatchModel(models.Model):
    """Stores trained matching model coefficients for AI scoring."""

    created_at = models.DateTimeField(auto_now_add=True)
    feature_order = models.JSONField()
    coef = models.JSONField()
    intercept = models.FloatField(default=0.0)
    sample_count = models.PositiveIntegerField(default=0)
    accuracy = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"MatchModel {self.pk} ({self.sample_count} samples)"
