from django.core.management.base import BaseCommand
from accounts.models import User, Course, Skill, StudentProfile, AdviserProfile, CoordinatorProfile, RequiredDocument, StudentDocument
from internship.models import Company, Internship, Application, CompanyReview
from django.utils import timezone
import random

class Command(BaseCommand):
    help = 'Seed complete dummy data for all models and features.'

    def handle(self, *args, **options):
        # Delete previous dummy data for a clean slate
        Application.objects.all().delete()
        CompanyReview.objects.all().delete()
        Internship.objects.all().delete()
        Company.objects.all().delete()
        StudentDocument.objects.all().delete()
        StudentProfile.objects.all().delete()
        AdviserProfile.objects.all().delete()
        CoordinatorProfile.objects.all().delete()
        User.objects.filter(email__in=[
            'coordinator@test.com', 'adviser@test.com', 'student@test.com'
        ]).delete()
        Skill.objects.all().delete()
        Course.objects.all().delete()
        RequiredDocument.objects.all().delete()

        # Courses
        courses = []
        for code, name in [
            ('BSIT', 'Bachelor of Science in Information Technology'),
            ('BSCS', 'Bachelor of Science in Computer Science'),
        ]:
            course, _ = Course.objects.get_or_create(code=code, name=name)
            courses.append(course)

        # Skills
        for course in courses:
            for i in range(1, 31):
                Skill.objects.get_or_create(name=f"{course.code} Skill {i}", course=course)

        # Required Documents
        for doc in [
            ('Resume', 'Student resume/CV'),
            ('Endorsement Letter', 'Letter from the school'),
            ('MOA', 'Memorandum of Agreement'),
        ]:
            RequiredDocument.objects.get_or_create(name=doc[0], description=doc[1])

        # Coordinator
        coordinator, _ = User.objects.get_or_create(email='coordinator@test.com', username='coordinator', user_type='COORDINATOR')
        coordinator.set_password('testpass123')
        coordinator.save()
        CoordinatorProfile.objects.get_or_create(user=coordinator, department='OJT Office')

        # Adviser
        adviser, _ = User.objects.get_or_create(email='adviser@test.com', username='adviser', user_type='ADVISER')
        adviser.set_password('testpass123')
        adviser.save()
        adviser_profile, _ = AdviserProfile.objects.get_or_create(user=adviser, department='IT Department')
        adviser_profile.courses.set([courses[0]])
        adviser_profile.sections = 'A,B'
        adviser_profile.save()

        # Student
        student, _ = User.objects.get_or_create(email='student@test.com', username='student', user_type='STUDENT')
        student.set_password('testpass123')
        student.save()
        student_profile, _ = StudentProfile.objects.get_or_create(user=student, course=courses[0], section='A', year_level='1', street='123 Main', barangay='Central', city='Bacoor', province='Cavite', phone_number='09171234567')
        student_profile.skills.set(Skill.objects.filter(course=courses[0])[:5])
        student_profile.save()

        # Student Document
        req_doc = RequiredDocument.objects.first()
        StudentDocument.objects.get_or_create(student=student_profile, document_type=req_doc, file='dummy.pdf')

        # Company
        company, _ = Company.objects.get_or_create(
            name='Test Company',
            defaults={
                'description': 'A test company for OJT',
                'company_email': 'company@test.com',
                'hr_email': 'hr@test.com',
                'phone_number': '1234567890',
                'street': '123 Main',
                'barangay': 'Central',
                'city': 'Bacoor',
                'province': 'Cavite',
                'latitude': 14.2294,
                'longitude': 120.9367,
                'status': 'ACTIVE',
                'has_incentives': True,
                'incentives_details': 'Allowance, Certificate',
                'added_by': coordinator,
            }
        )

        # Internship
        internship, _ = Internship.objects.get_or_create(
            company=company,
            title='IT Internship',
            description='IT OJT',
        )
        internship.recommended_courses.set([courses[0]])
        internship.required_skills.set(Skill.objects.filter(course=courses[0])[:3])
        internship.save()

        # Application
        Application.objects.get_or_create(student=student_profile, internship=internship, status='PENDING')

        # Company Review
        CompanyReview.objects.get_or_create(student=student_profile, company=company, rating=5, comment='Great company!', is_anonymous=False)

        self.stdout.write(self.style.SUCCESS('Dummy data created for all models and features.'))
