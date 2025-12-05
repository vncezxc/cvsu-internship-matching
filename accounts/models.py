from django.db import models
from django.conf import settings
import random
# 6-digit email verification code model
class EmailVerificationCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.code}"

    @staticmethod
    def generate_code():
        return '{:06d}'.format(random.randint(0, 999999))
# DTR (Daily Time Record) model for weekly DTR submission
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
import os


class DTR(models.Model):
    student = models.ForeignKey('StudentProfile', on_delete=models.CASCADE, related_name='dtrs')
    adviser = models.ForeignKey('AdviserProfile', on_delete=models.CASCADE, related_name='dtrs')
    week_start = models.DateField(help_text="Start of the week (Monday)")
    week_end = models.DateField(help_text="End of the week (Sunday)")
    file = models.FileField(upload_to='dtr_files/', validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])])
    hours_rendered = models.PositiveIntegerField(default=0, help_text="OJT hours rendered for this week")
    submitted_at = models.DateTimeField(default=timezone.now)
    approved = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ('student', 'week_start')
        ordering = ['-week_start']

    def __str__(self):
        return f"DTR: {self.student.user.get_full_name()} ({self.week_start} - {self.week_end})"
    
class UserManager(BaseUserManager):
    """Custom user manager for our User model."""
    
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'ADMIN')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, username, password, **extra_fields)

class User(AbstractUser):
    """Custom User model with additional fields for user type."""
    
    class UserType(models.TextChoices):
        STUDENT = 'STUDENT', _('Student')
        ADVISER = 'ADVISER', _('OJT Adviser')
        COORDINATOR = 'COORDINATOR', _('OJT Coordinator')
        ADMIN = 'ADMIN', _('Admin')
    
    email = models.EmailField(_('email address'), unique=True)
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.STUDENT,
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    @property
    def is_student(self):
        return self.user_type == self.UserType.STUDENT
    
    @property
    def is_adviser(self):
        return self.user_type == self.UserType.ADVISER
    
    @property
    def is_coordinator(self):
        return self.user_type == self.UserType.COORDINATOR

class Course(models.Model):
    """Model for academic courses offered by CVSU."""
    
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    required_ojt_hours = models.PositiveIntegerField(default=300)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Skill(models.Model):
    """Model for skills that can be associated with students and internships."""
    
    name = models.CharField(max_length=100, unique=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='skills', null=True, blank=True)
    
    def __str__(self):
        return self.name

def student_cv_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/user_<id>/cv/<filename>
    return f'user_{instance.user.id}/cv/{filename}'

def student_document_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/user_<id>/documents/<filename>
    return f'user_{instance.student.user.id}/documents/{filename}'

class StudentProfile(models.Model):
    def save(self, *args, **kwargs):
        # Automatically set status to COMPLETED if progress is 100% and not already completed
        if self.course and self.course.required_ojt_hours > 0:
            progress = (self.ojt_hours_completed / self.course.required_ojt_hours) * 100
            if progress >= 100 and self.ojt_status != self.OJTStatus.COMPLETED:
                self.ojt_status = self.OJTStatus.COMPLETED
        super().save(*args, **kwargs)

    @property
    def student_ojt_status_choices(self):
        # Choices visible to students (COMPLETED excluded)
        return [
            (self.OJTStatus.LOOKING, self.OJTStatus.LOOKING.label),
            (self.OJTStatus.WAITING, self.OJTStatus.WAITING.label),
            (self.OJTStatus.ONGOING, self.OJTStatus.ONGOING.label),
            (self.OJTStatus.REJECTED, self.OJTStatus.REJECTED.label),
        ]

    def get_ojt_status_display_student(self):
        # Display label for students (COMPLETED hidden)
        if self.ojt_status == self.OJTStatus.COMPLETED:
            return ""
        return self.get_ojt_status_display()
    def get_profile_completion_percentage(self):
        """
        Calculate profile completion based on required fields filled.
        Adjust the fields as needed for your definition of 'complete'.
        """
        required_fields = [
            self.user.first_name,
            self.user.last_name,
            self.user.email,
            self.student_id,
            self.course,
            self.year_level,
            self.section,
            self.phone_number,
            self.street,
            self.barangay,
            self.city,
            self.province,
            self.profile_image,
        ]
        filled = sum(1 for f in required_fields if f)
        total = len(required_fields)
        return int((filled / total) * 100) if total > 0 else 0
    """Extended profile for Student users."""
    
    class YearLevel(models.TextChoices):
        FIRST = '1', _('1st Year')
        SECOND = '2', _('2nd Year')
        THIRD = '3', _('3rd Year')
        FOURTH = '4', _('4th Year')
        FIFTH = '5', _('5th Year')

    class OJTStatus(models.TextChoices):
        LOOKING = 'LOOKING', _('Still Looking')
        WAITING = 'WAITING', _('Waiting for Response')
        ONGOING = 'ONGOING', _('Currently Undergoing OJT')
        REJECTED = 'REJECTED', _('All Applications Rejected')
        COMPLETED = 'COMPLETED', _('Completed')
    def can_update_ojt_hours(self, acting_user):
        """
        Only advisers can update OJT hours, and only if status is 'Currently Undergoing OJT'.
        """
        is_adviser = hasattr(acting_user, 'adviser_profile')
        return is_adviser and self.ojt_status == self.OJTStatus.ONGOING
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=32, unique=True, blank=True, null=True, help_text="Student ID number")
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, related_name='students')
    year_level = models.CharField(max_length=1, choices=YearLevel.choices, default=YearLevel.FIRST)
    section = models.CharField(max_length=10, blank=True)
    skills = models.ManyToManyField(Skill, related_name='students', blank=True)
    
    # Address fields
    street = models.CharField(max_length=255, blank=True)
    barangay = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    
    # New fields
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Location coordinates for map
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # OJT related fields
    ojt_status = models.CharField(max_length=20, choices=OJTStatus.choices, default=OJTStatus.LOOKING)
    ojt_hours_completed = models.PositiveIntegerField(default=0)
    cv = models.FileField(
        upload_to=student_cv_path, 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])]
    )
    
    # Profile completeness
    is_profile_complete = models.BooleanField(default=False)
    
    # Profile image
    profile_image = models.ImageField(upload_to='student_profiles/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} ({self.student_id})'s Profile" if self.student_id else f"{self.user.username}'s Profile"
    
    def get_full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    def get_full_address(self):
        return f"{self.street}, {self.barangay}, {self.city}, {self.province}"
    
    def get_progress_percentage(self):
        """Calculate the OJT progress percentage."""
        if self.course and self.course.required_ojt_hours > 0:
            return min(100, int((self.ojt_hours_completed / self.course.required_ojt_hours) * 100))
        return 0
    
    def get_ojt_status_color(self):
        """Return the Bootstrap color class based on OJT status."""
        status_colors = {
            self.OJTStatus.LOOKING: 'primary',
            self.OJTStatus.WAITING: 'warning',
            self.OJTStatus.ONGOING: 'info',
            self.OJTStatus.REJECTED: 'danger',
            self.OJTStatus.COMPLETED: 'success'
        }
        return status_colors.get(self.OJTStatus(self.ojt_status), 'secondary')
    
    @property
    def ojt_hours_required(self):
        """Return the required OJT hours for the student's course."""
        if self.course:
            return self.course.required_ojt_hours
        return 300  # Default value if no course is assigned
    
    @property
    def profile_is_complete_for_matching(self):
        """
        Returns True if the student profile has the minimum required fields for internship matching:
        - course is set
        - at least one skill is present
        - both latitude and longitude (pinned location) are set
        """
        has_course = self.course is not None
        has_skills = self.skills.exists()
        has_location = self.latitude is not None and self.longitude is not None
        return has_course and has_skills and has_location

class RequiredDocument(models.Model):
    """Model for required OJT documents."""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)
    template_file = models.FileField(
        upload_to='document_templates/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx'])],
        blank=True, null=True,
        help_text='PDF template for this document (uploaded by coordinator)'
    )
    
    def __str__(self):
        return self.name

class StudentDocument(models.Model):
    """Model for student uploaded documents."""
    
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='documents')
    document_type = models.ForeignKey(RequiredDocument, on_delete=models.CASCADE, related_name='student_documents')
    file = models.FileField(
        upload_to=student_document_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'docx', 'jpg', 'jpeg', 'png'])]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False, help_text='Set to True when adviser accepts the document')
    
    def __str__(self):
        return f"{self.document_type.name} - {self.student.user.username}"
    
    def filename(self):
        return os.path.basename(self.file.name)

class AdviserProfile(models.Model):
    """Extended profile for OJT Adviser users."""
    
    class YearLevel(models.TextChoices):
        FIRST = '1', _('1st Year')
        SECOND = '2', _('2nd Year')
        THIRD = '3', _('3rd Year')
        FOURTH = '4', _('4th Year')
        FIFTH = '5', _('5th Year')

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='adviser_profile')
    department = models.CharField(max_length=100)
    courses = models.ManyToManyField(Course, related_name='advisers')
    sections = models.CharField(max_length=255, blank=True, help_text="Comma-separated list of sections")
    # Profile image for adviser
    profile_image = models.ImageField(upload_to='adviser_profiles/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    office = models.CharField(max_length=100, blank=True)
    year_levels = models.CharField(max_length=20, blank=True, help_text="Comma-separated year levels handled (e.g. 1,2,3)")
    # Remove old year_level field if present
    
    def get_year_levels_display(self):
        if not self.year_levels:
            return ''
        levels = self.year_levels.split(',')
        display = []
        for lvl in levels:
            val = dict(self.YearLevel.choices).get(lvl, lvl)
            display.append(str(val))  # Ensure all are strings
        return ', '.join(display)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.department}"
    
    def get_sections_list(self):
        return [s.strip() for s in self.sections.split(',') if s.strip()]
    
    def get_student_count(self):
        return StudentProfile.objects.filter(
            course__in=self.courses.all(),
            section__in=self.get_sections_list()
        ).count()

class CoordinatorProfile(models.Model):
    """Extended profile for OJT Coordinator users."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='coordinator_profile')
    department = models.CharField(max_length=100)
    # Profile image for coordinator
    profile_image = models.ImageField(upload_to='coordinator_profiles/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    office = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.department}"
