from django.core.management.base import BaseCommand
from accounts.models import User, AdviserProfile, Course, Skill

# Realistic skills per course (sample, can be expanded)
COURSE_SKILLS = {
    'BSIT': [
        'Python Programming', 'Java Programming', 'Web Development', 'Database Management', 'Networking',
        'Linux Administration', 'Cybersecurity', 'Mobile App Development', 'Cloud Computing', 'UI/UX Design',
        'Software Testing', 'Agile Methodologies', 'Data Structures', 'Algorithms', 'System Analysis',
        'Project Management', 'Technical Support', 'IT Documentation', 'API Integration', 'DevOps Basics',
        'Version Control (Git)', 'PHP', 'JavaScript', 'C#', 'ASP.NET', 'ReactJS',
        'Node.js', 'Django', 'Flask', 'Machine Learning', 'Data Visualization'
    ],
    'BSCS': [
        'C++ Programming', 'Java Programming', 'Python Programming', 'Algorithms', 'Data Structures',
        'Artificial Intelligence', 'Machine Learning', 'Operating Systems', 'Compiler Design', 'Discrete Math',
        'Database Systems', 'Software Engineering', 'Web Development', 'Mobile Computing', 'Computer Graphics',
        'Network Security', 'Cloud Computing', 'Parallel Computing', 'Theory of Computation', 'Numerical Analysis',
        'Data Mining', 'Big Data', 'Natural Language Processing', 'Robotics', 'Game Development',
        'Computer Vision', 'Information Retrieval', 'Distributed Systems', 'Blockchain', 'Quantum Computing'
    ],
    'BSPSY': [
        'Counseling', 'Psychological Assessment', 'Research Methods', 'Statistics', 'Clinical Psychology',
        'Developmental Psychology', 'Abnormal Psychology', 'Social Psychology', 'Industrial Psychology', 'Forensic Psychology',
        'Neuropsychology', 'Cognitive Psychology', 'Behavioral Therapy', 'Group Dynamics', 'Test Construction',
        'Interviewing Skills', 'Case Management', 'Crisis Intervention', 'Community Psychology', 'Health Psychology',
        'Educational Psychology', 'Child Psychology', 'Aging and Gerontology', 'Addiction Counseling', 'Family Therapy',
        'Organizational Behavior', 'Human Resource Management', 'Program Evaluation', 'Ethics in Psychology', 'Multicultural Counseling'
    ],
    'BSCRIM': [
        'Criminal Law', 'Forensic Science', 'Investigation Techniques', 'Police Operations', 'Criminological Research',
        'Self-Defense', 'Firearms Proficiency', 'Crime Scene Management', 'Cybercrime', 'Juvenile Justice',
        'Correctional Administration', 'Victimology', 'Security Management', 'Disaster Response', 'Traffic Management',
        'Community Policing', 'Human Rights', 'Drug Education', 'Legal Medicine', 'Court Testimony',
        'Fingerprint Analysis', 'Lie Detection', 'Ballistics', 'Forensic Photography', 'Report Writing',
        'Interview and Interrogation', 'Surveillance', 'Evidence Handling', 'Criminal Profiling', 'Public Safety Awareness'
    ],
    'BSED_MATH': [
        'Algebra', 'Geometry', 'Trigonometry', 'Calculus', 'Statistics',
        'Mathematical Proofs', 'Number Theory', 'Linear Algebra', 'Differential Equations', 'Math Modeling',
        'Math Lesson Planning', 'Assessment Design', 'Math Technology Tools', 'Math Research', 'Math Communication',
        'Math Curriculum Development', 'Math Remediation', 'Math Games', 'Math History', 'Math for Early Grades',
        'Math for Secondary Grades', 'Math for STEM', 'Math for Business', 'Math for Engineering', 'Math for Social Sciences',
        'Math for Everyday Life', 'Math Problem Solving', 'Math Enrichment', 'Math Coaching', 'Math Club Advising'
    ],
    'BSED_ENG': [
        'English Grammar', 'Literature Analysis', 'Creative Writing', 'Speech Communication', 'Language Assessment',
        'English for Academic Purposes', 'English for Specific Purposes', 'English Curriculum Design', 'Remedial English', 'English Research',
        'English Lesson Planning', 'English Technology Tools', 'English for Early Grades', 'English for Secondary Grades', 'English for STEM',
        'English for Business', 'English for Engineering', 'English for Social Sciences', 'English for Everyday Life', 'English for Media',
        'Public Speaking', 'Debate Coaching', 'Drama Production', 'Reading Intervention', 'Writing Center Tutoring',
        'ESL Teaching', 'TOEFL/IELTS Prep', 'Language Policy', 'Multicultural Education', 'Children’s Literature'
    ],
    'BSHM': [
        'Food Preparation', 'Beverage Mixing', 'Front Office Operations', 'Housekeeping', 'Event Planning',
        'Customer Service', 'Culinary Arts', 'Bakery and Pastry', 'Barista Skills', 'Wine Appreciation',
        'Hotel Management', 'Travel and Tour Operations', 'Resort Management', 'Restaurant Management', 'Cost Control',
        'Menu Planning', 'Food Safety', 'Sanitation', 'Hospitality Marketing', 'Hospitality Accounting',
        'Hospitality Law', 'Hospitality HR', 'Hospitality IT', 'Hospitality English', 'Hospitality Research',
        'Hospitality Entrepreneurship', 'Sustainable Tourism', 'Cultural Awareness', 'Guest Relations', 'Banquet Management'
    ],
    'BSBM_MKT': [
        'Marketing Research', 'Consumer Behavior', 'Brand Management', 'Sales Management', 'Digital Marketing',
        'Advertising', 'Retail Management', 'Product Development', 'Pricing Strategies', 'Market Analysis',
        'Public Relations', 'Event Marketing', 'Social Media Marketing', 'E-commerce', 'Business Analytics',
        'Customer Relationship Management', 'Distribution Management', 'International Marketing', 'Marketing Strategy', 'Market Segmentation',
        'Promotions', 'Trade Marketing', 'B2B Marketing', 'Service Marketing', 'Marketing Ethics',
        'Sales Forecasting', 'Negotiation Skills', 'Presentation Skills', 'Market Research Tools', 'Brand Storytelling'
    ],
    'BSBM_HR': [
        'Recruitment', 'Training and Development', 'Compensation and Benefits', 'Labor Relations', 'Performance Management',
        'HR Analytics', 'Organizational Development', 'HR Policy', 'HR Law', 'HR Information Systems',
        'Employee Engagement', 'Conflict Resolution', 'Talent Management', 'Succession Planning', 'Diversity and Inclusion',
        'Workforce Planning', 'Change Management', 'HR Metrics', 'Payroll Management', 'Employee Relations',
        'Job Analysis', 'Job Evaluation', 'HR Communication', 'HR Research', 'HR for SMEs',
        'HR for Startups', 'HR for Multinationals', 'HR for Government', 'HR for Nonprofits', 'HR for Education'
    ],
}

class Command(BaseCommand):
    help = "Create an adviser who handles all courses and adds 30 real skills per course (deletes previous ones)"

    def handle(self, *args, **kwargs):
        adviser_email = "superadviser@test.com"
        # Delete previous super adviser and all skills
        User.objects.filter(email=adviser_email).delete()
        Skill.objects.all().delete()
        self.stdout.write(self.style.WARNING("Deleted previous super adviser and all skills."))

        adviser, created = User.objects.get_or_create(
            email=adviser_email,
            defaults={
                "username": "superadviser",
                "user_type": "ADVISER",
            }
        )
        adviser.set_password("testpass123")
        adviser.save()
        self.stdout.write(self.style.SUCCESS(f"Adviser user created: {adviser_email}"))

        courses = Course.objects.all()
        adviser_profile, _ = AdviserProfile.objects.get_or_create(user=adviser)
        adviser_profile.courses.set(courses)
        adviser_profile.save()
        self.stdout.write(self.style.SUCCESS(f"Adviser assigned to all courses."))

        for course in courses:
            code = course.code
            real_skills = COURSE_SKILLS.get(code, [])
            if len(real_skills) < 30:
                real_skills += [f"{code} Extra Skill {i}" for i in range(len(real_skills)+1, 31)]
            for skill_name in real_skills[:30]:
                # Ensure skill name is unique across all courses
                unique_skill_name = skill_name
                if Skill.objects.filter(name=skill_name).exists():
                    unique_skill_name = f"{skill_name} ({code})"
                Skill.objects.get_or_create(name=unique_skill_name, course=course)
            self.stdout.write(self.style.SUCCESS(f"Ensured 30 real skills for course: {course.code}"))

        self.stdout.write(self.style.SUCCESS("Super adviser setup complete!"))
