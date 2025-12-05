from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User, StudentProfile, Skill, Course

class Company(models.Model):
    """Model for companies offering internships."""
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
    
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
    
    def __str__(self):
        return self.name
    
    def get_full_address(self):
        return f"{self.street}, {self.barangay}, {self.city}, {self.province}"
    
    def get_active_internships_count(self):
        return self.internships.filter(is_active=True).count()

class Internship(models.Model):
    """Model for internship opportunities."""
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='internships')
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Recommended courses and skills
    recommended_courses = models.ManyToManyField(Course, related_name='recommended_internships')
    required_skills = models.ManyToManyField(Skill, related_name='required_by_internships')
    
    # Internship details
    is_active = models.BooleanField(default=True)
    slots_available = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} at {self.company.name}"
    
    def get_match_score(self, student_profile):
        """Calculate match score between internship and student (0-100)."""
        if not student_profile.course or not student_profile.skills.exists():
            return 0
        
        # Course match (40% weight)
        course_match = 40 if student_profile.course in self.recommended_courses.all() else 0
        
        # Skills match (60% weight)
        student_skills = set(student_profile.skills.all())
        internship_skills = set(self.required_skills.all())
        
        if not internship_skills:
            skill_match = 60  # If no skills required, full score
        else:
            matching_skills = student_skills.intersection(internship_skills)
            skill_match = int((len(matching_skills) / len(internship_skills)) * 60)
        
        return course_match + skill_match

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
        super().save(*args, **kwargs)

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
