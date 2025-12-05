from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.utils import timezone
import random
from datetime import timedelta

from accounts.models import User, Course, Skill, StudentProfile, RequiredDocument, AdviserProfile, CoordinatorProfile
from internship.models import Company, Internship, Application
from dashboard.models import DashboardStatistics

class Command(BaseCommand):
    help = 'Create test data for the CVSU Internship Matching System'
    
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Creating test data...'))
        
        # Create courses
        self.create_courses()
        
        # Create skills
        self.create_skills()
        
        # Create required documents
        self.create_required_documents()
        
        # Create users and profiles
        self.create_users()
        
        # Create companies and internships
        self.create_companies()
        
        # Create applications
        self.create_applications()
        
        # Create statistics
        self.create_statistics()
        
        self.stdout.write(self.style.SUCCESS('Test data created successfully!'))
    
    def create_courses(self):
        self.stdout.write('Creating courses...')
        
        courses = [
            {'code': 'BSCS', 'name': 'BS Computer Science', 'required_ojt_hours': 300},
            {'code': 'BSIT', 'name': 'BS Information Technology', 'required_ojt_hours': 300},
            {'code': 'BSIS', 'name': 'BS Information Systems', 'required_ojt_hours': 300},
            {'code': 'BSECE', 'name': 'BS Electronics Engineering', 'required_ojt_hours': 400},
            {'code': 'BSA', 'name': 'BS Accountancy', 'required_ojt_hours': 350},
        ]
        
        for course_data in courses:
            Course.objects.get_or_create(
                code=course_data['code'],
                defaults={
                    'name': course_data['name'],
                    'required_ojt_hours': course_data['required_ojt_hours'],
                    'description': f"This is the {course_data['name']} program."
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(courses)} courses'))
    
    def create_skills(self):
        self.stdout.write('Creating skills...')
        
        # IT Skills
        it_course = Course.objects.get(code='BSIT')
        it_skills = [
            'Python', 'Java', 'C++', 'JavaScript', 'HTML/CSS', 'React',
            'Angular', 'Node.js', 'Django', 'Flask', 'Spring Boot'
        ]
        
        # IS Skills
        is_course = Course.objects.get(code='BSIS')
        is_skills = [
            'Database Design', 'SQL', 'Data Analysis', 'BI Tools', 
            'Systems Analysis', 'ERP Systems', 'Project Management'
        ]
        
        # ECE Skills
        ece_course = Course.objects.get(code='BSECE')
        ece_skills = [
            'Circuit Design', 'PCB Layout', 'Microcontrollers', 'VHDL',
            'Electronic Testing', 'Signal Processing', 'Embedded Systems'
        ]
        
        # Accounting Skills
        acc_course = Course.objects.get(code='BSA')
        acc_skills = [
            'Financial Accounting', 'Taxation', 'Auditing', 'Cost Accounting',
            'Bookkeeping', 'Financial Analysis', 'QuickBooks', 'Microsoft Excel'
        ]
        
        # Generic Skills
        generic_skills = [
            'Communication', 'Problem Solving', 'Teamwork', 'Leadership',
            'Time Management', 'Analytical Thinking', 'Attention to Detail'
        ]
        
        # Create IT Skills
        for skill_name in it_skills:
            Skill.objects.get_or_create(name=skill_name, defaults={'course': it_course})
        
        # Create IS Skills
        for skill_name in is_skills:
            Skill.objects.get_or_create(name=skill_name, defaults={'course': is_course})
        
        # Create ECE Skills
        for skill_name in ece_skills:
            Skill.objects.get_or_create(name=skill_name, defaults={'course': ece_course})
        
        # Create Accounting Skills
        for skill_name in acc_skills:
            Skill.objects.get_or_create(name=skill_name, defaults={'course': acc_course})
        
        # Create Generic Skills
        for skill_name in generic_skills:
            Skill.objects.get_or_create(name=skill_name, defaults={'course': None})
        
        total_skills = len(it_skills) + len(is_skills) + len(ece_skills) + len(acc_skills) + len(generic_skills)
        self.stdout.write(self.style.SUCCESS(f'Created {total_skills} skills'))
    
    def create_required_documents(self):
        self.stdout.write('Creating required documents...')
        
        documents = [
            {'name': 'OJT Application Letter', 'is_required': True},
            {'name': 'Resume/CV', 'is_required': True},
            {'name': 'School ID', 'is_required': True},
            {'name': 'Medical Certificate', 'is_required': True},
            {'name': 'Proof of Insurance', 'is_required': True},
            {'name': 'Certificate of Good Moral Character', 'is_required': True},
            {'name': 'Parent/Guardian Consent', 'is_required': True},
            {'name': 'OJT Completion Certificate', 'is_required': False},
        ]
        
        for doc_data in documents:
            RequiredDocument.objects.get_or_create(
                name=doc_data['name'],
                defaults={'is_required': doc_data['is_required']}
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(documents)} required documents'))
    
    def create_users(self):
        self.stdout.write('Creating users...')
        
        # Create admin user
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@cvsu.edu.ph',
                'password': make_password('admin123'),
                'first_name': 'System',
                'last_name': 'Administrator',
                'user_type': User.UserType.ADMIN,
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        # Create coordinator
        coordinator, created = User.objects.get_or_create(
            username='coordinator',
            defaults={
                'email': 'coordinator@cvsu.edu.ph',
                'password': make_password('coordinator123'),
                'first_name': 'OJT',
                'last_name': 'Coordinator',
                'user_type': User.UserType.COORDINATOR
            }
        )
        
        # Create coordinator profile
        CoordinatorProfile.objects.get_or_create(
            user=coordinator,
            defaults={
                'department': 'Computer Science Department',
                'position': 'OJT Coordinator'
            }
        )
        
        # Create advisers
        adviser_data = [
            {
                'username': 'adviser1',
                'email': 'adviser1@cvsu.edu.ph',
                'first_name': 'John',
                'last_name': 'Doe',
                'department': 'Computer Science Department',
                'courses': ['BSCS', 'BSIT'],
                'sections': 'CS-4A, IT-4A, IT-4B'
            },
            {
                'username': 'adviser2',
                'email': 'adviser2@cvsu.edu.ph',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'department': 'Information Systems Department',
                'courses': ['BSIS'],
                'sections': 'IS-4A, IS-4B'
            },
            {
                'username': 'adviser3',
                'email': 'adviser3@cvsu.edu.ph',
                'first_name': 'Robert',
                'last_name': 'Johnson',
                'department': 'Accountancy Department',
                'courses': ['BSA'],
                'sections': 'ACC-4A, ACC-4B'
            }
        ]
        
        for adviser_info in adviser_data:
            adviser, created = User.objects.get_or_create(
                username=adviser_info['username'],
                defaults={
                    'email': adviser_info['email'],
                    'password': make_password('adviser123'),
                    'first_name': adviser_info['first_name'],
                    'last_name': adviser_info['last_name'],
                    'user_type': User.UserType.ADVISER
                }
            )
            
            # Create adviser profile
            profile, created = AdviserProfile.objects.get_or_create(
                user=adviser,
                defaults={
                    'department': adviser_info['department'],
                    'sections': adviser_info['sections']
                }
            )
            
            # Add courses
            if created:
                for course_code in adviser_info['courses']:
                    course = Course.objects.get(code=course_code)
                    profile.courses.add(course)
        
        # Create students
        courses = Course.objects.all()
        sections = ['A', 'B', 'C']
        
        created_students = 0
        for i in range(1, 21):
            course = random.choice(courses)
            section = f"{course.code[-2:]}-4{random.choice(sections)}"
            
            student, created = User.objects.get_or_create(
                username=f'student{i}',
                defaults={
                    'email': f'student{i}@cvsu.edu.ph',
                    'password': make_password('student123'),
                    'first_name': f'Student{i}',
                    'last_name': f'User{i}',
                    'user_type': User.UserType.STUDENT
                }
            )
            
            if created or not hasattr(student, 'student_profile'):
                created_students += 1
                # Create student profile
                profile = StudentProfile.objects.create(
                    user=student,
                    course=course,
                    year_level='4',
                    section=section,
                    ojt_status=random.choice(list(StudentProfile.OJTStatus.choices))[0],
                    ojt_hours_completed=random.randint(0, course.required_ojt_hours),
                    student_id=f'2023{i:05d}',
                    contact_number=f'09{random.randint(100000000, 999999999)}',
                    street=f'Street {i}',
                    barangay=f'Barangay {i}',
                    city='Bacoor',
                    province='Cavite',
                    is_profile_complete=True
                )
                
                # Add random skills
                all_skills = list(Skill.objects.all())
                profile_skills = random.sample(all_skills, min(random.randint(3, 8), len(all_skills)))
                for skill in profile_skills:
                    profile.skills.add(skill)
        
        self.stdout.write(self.style.SUCCESS(
            f'Created users: 1 admin, 1 coordinator, {len(adviser_data)} advisers, {created_students} students'
        ))
    
    def create_companies(self):
        self.stdout.write('Creating companies and internships...')
        
        companies_data = [
            {
                'name': 'TechNova Solutions',
                'description': 'A leading IT solutions provider with focus on web and mobile development',
                'email': 'hr@technova.com',
                'industry': 'Information Technology',
                'address': 'Bacoor, Cavite'
            },
            {
                'name': 'DataSphere Analytics',
                'description': 'Specializing in big data analytics and business intelligence solutions',
                'email': 'careers@datasphere.com',
                'industry': 'Data Analytics',
                'address': 'Makati City, Metro Manila'
            },
            {
                'name': 'ElectroTech Systems',
                'description': 'Electronics manufacturing and systems integration company',
                'email': 'jobs@electrotech.com',
                'industry': 'Electronics',
                'address': 'Imus, Cavite'
            },
            {
                'name': 'FinSecure Accounting',
                'description': 'Financial services and accounting solutions for businesses',
                'email': 'internship@finsecure.com',
                'industry': 'Accounting & Finance',
                'address': 'Alabang, Muntinlupa'
            },
            {
                'name': 'CloudNet Solutions',
                'description': 'Cloud computing and networking solutions provider',
                'email': 'recruit@cloudnet.com',
                'industry': 'Information Technology',
                'address': 'Dasmariñas, Cavite'
            }
        ]
        
        coordinator = User.objects.get(username='coordinator')
        created_companies = 0
        created_internships = 0
        
        for company_data in companies_data:
            company, created = Company.objects.get_or_create(
                name=company_data['name'],
                defaults={
                    'description': company_data['description'],
                    'company_email': company_data['email'],
                    'hr_email': company_data['email'],
                    'phone_number': f'09{random.randint(100000000, 999999999)}',
                    'street': f"{random.randint(1, 100)} {company_data['name'].split()[0]} Street",
                    'barangay': f"Barangay {random.randint(1, 30)}",
                    'city': company_data['address'].split(',')[0],
                    'province': company_data['address'].split(',')[1].strip(),
                    'status': Company.Status.ACTIVE,
                    'has_incentives': random.choice([True, False]),
                    'added_by': coordinator
                }
            )
            
            if created:
                created_companies += 1
            
            # Create internships for this company
            num_internships = random.randint(1, 3)
            for j in range(num_internships):
                if company_data['industry'] == 'Information Technology':
                    courses = Course.objects.filter(code__in=['BSCS', 'BSIT', 'BSIS'])
                    title = random.choice(['Software Developer Intern', 'Web Developer Intern', 'Mobile Developer Intern', 'QA Intern'])
                elif company_data['industry'] == 'Data Analytics':
                    courses = Course.objects.filter(code__in=['BSCS', 'BSIT', 'BSIS'])
                    title = random.choice(['Data Analyst Intern', 'Business Intelligence Intern', 'Database Developer Intern'])
                elif company_data['industry'] == 'Electronics':
                    courses = Course.objects.filter(code__in=['BSECE'])
                    title = random.choice(['Electronics Engineer Intern', 'IoT Developer Intern', 'Systems Integrator Intern'])
                elif company_data['industry'] == 'Accounting & Finance':
                    courses = Course.objects.filter(code__in=['BSA'])
                    title = random.choice(['Accounting Intern', 'Financial Analyst Intern', 'Audit Assistant Intern'])
                else:
                    courses = Course.objects.all()
                    title = f"{company_data['industry']} Intern"
                
                internship, created = Internship.objects.get_or_create(
                    company=company,
                    title=title,
                    defaults={
                        'description': f"This is an internship opportunity at {company.name} for {title} position.",
                        'is_active': True,
                        'slots_available': random.randint(1, 5)
                    }
                )
                
                if created:
                    created_internships += 1
                    # Add recommended courses
                    for course in courses:
                        internship.recommended_courses.add(course)
                    
                    # Add required skills
                    course_skills = Skill.objects.filter(course__in=courses)
                    required_skills = random.sample(list(course_skills), min(random.randint(2, 5), course_skills.count()))
                    for skill in required_skills:
                        internship.required_skills.add(skill)
        
        self.stdout.write(self.style.SUCCESS(f'Created {created_companies} companies and {created_internships} internships'))
    
    def create_applications(self):
        self.stdout.write('Creating applications...')
        
        students = StudentProfile.objects.all()
        internships = Internship.objects.all()
        
        created_applications = 0
        for student in students:
            # Find matching internships for this student's course
            matching_internships = internships.filter(recommended_courses=student.course)
            
            # Apply to 0-3 random internships
            num_applications = random.randint(0, min(3, matching_internships.count()))
            if num_applications > 0:
                selected_internships = random.sample(list(matching_internships), num_applications)
                
                for internship in selected_internships:
                    status_choices = [s[0] for s in Application.Status.choices]
                    status_weights = [0.4, 0.3, 0.2, 0.1]  # PENDING, ACCEPTED, REJECTED, COMPLETED
                    
                    application, created = Application.objects.get_or_create(
                        student=student,
                        internship=internship,
                        defaults={
                            'status': random.choices(status_choices, weights=status_weights)[0],
                            'match_score': internship.get_match_score(student),
                            'notes': 'This is a test application.'
                        }
                    )
                    
                    if created:
                        created_applications += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {created_applications} applications'))
    
    def create_statistics(self):
        self.stdout.write('Creating dashboard statistics...')
        
        # Generate statistics for the past 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Get current counts
        total_students = StudentProfile.objects.count()
        looking_students = StudentProfile.objects.filter(ojt_status=StudentProfile.OJTStatus.LOOKING).count()
        waiting_students = StudentProfile.objects.filter(ojt_status=StudentProfile.OJTStatus.WAITING).count()
        ongoing_students = StudentProfile.objects.filter(ojt_status=StudentProfile.OJTStatus.ONGOING).count()
        completed_students = StudentProfile.objects.filter(ojt_status=StudentProfile.OJTStatus.COMPLETED).count()
        
        total_companies = Company.objects.count()
        active_companies = Company.objects.filter(status=Company.Status.ACTIVE).count()
        
        total_internships = Internship.objects.count()
        active_internships = Internship.objects.filter(is_active=True).count()
        
        total_applications = Application.objects.count()
        pending_applications = Application.objects.filter(status=Application.Status.PENDING).count()
        accepted_applications = Application.objects.filter(status=Application.Status.ACCEPTED).count()
        rejected_applications = Application.objects.filter(status=Application.Status.REJECTED).count()
        
        # Generate statistics for each day with small random variations
        created_stats = 0
        for i in range(31):
            current_date = start_date + timedelta(days=i)
            
            # Add small random variations to the counts
            def random_variation(count):
                return max(0, count + random.randint(-2, 2))
            
            stats, created = DashboardStatistics.objects.get_or_create(
                date=current_date,
                defaults={
                    'total_students': random_variation(total_students),
                    'students_looking': random_variation(looking_students),
                    'students_waiting': random_variation(waiting_students),
                    'students_ongoing': random_variation(ongoing_students),
                    'students_completed': random_variation(completed_students),
                    'total_companies': random_variation(total_companies),
                    'active_companies': random_variation(active_companies),
                    'total_internships': random_variation(total_internships),
                    'active_internships': random_variation(active_internships),
                    'total_applications': random_variation(total_applications),
                    'pending_applications': random_variation(pending_applications),
                    'accepted_applications': random_variation(accepted_applications),
                    'rejected_applications': random_variation(rejected_applications)
                }
            )
            
            if created:
                created_stats += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {created_stats} statistics records')) 