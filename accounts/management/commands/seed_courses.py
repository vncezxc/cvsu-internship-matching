from django.core.management.base import BaseCommand
from accounts.models import Course, Skill, AdviserProfile
from django.contrib.auth import get_user_model

# Official CVSU Bacoor Campus courses only
COURSES = [
    {"code": "BSIT", "name": "Bachelor of Science in Information Technology", "required_ojt_hours": 486},
    {"code": "BSCS", "name": "Bachelor of Science in Computer Science", "required_ojt_hours": 486},
    {"code": "BSPSY", "name": "Bachelor of Science in Psychology", "required_ojt_hours": 486},
    {"code": "BSCRIM", "name": "Bachelor of Science in Criminology", "required_ojt_hours": 486},
    {"code": "BSED_MATH", "name": "Bachelor of Secondary Education (Math)", "required_ojt_hours": 486},
    {"code": "BSED_ENG", "name": "Bachelor of Secondary Education (English)", "required_ojt_hours": 486},
    {"code": "BSHM", "name": "Bachelor of Science in Hospitality Management", "required_ojt_hours": 486},
    {"code": "BSBM_MKT", "name": "BS in Business Management (Marketing)", "required_ojt_hours": 486},
    {"code": "BSBM_HR", "name": "BS in Business Management (Human Resources)", "required_ojt_hours": 486},
]

SKILLS = {
    "BSIT": [
        "Python Programming", "Web Development", "Database Management", "Network Security", "Mobile App Development",
        "Cloud Computing", "UI/UX Design", "Data Structures", "Algorithms", "Software Engineering",
        "Linux Administration", "IT Support", "Cybersecurity", "Java Programming", "C# Development",
        "PHP Development", "JavaScript", "DevOps", "Machine Learning", "Data Analysis",
        "API Integration", "Version Control (Git)", "Agile Methodologies", "Technical Writing", "Project Management",
        "System Analysis", "Computer Hardware", "Virtualization", "Shell Scripting", "Troubleshooting"
    ],
    "BSCS": [
        "Artificial Intelligence", "Machine Learning", "Data Science", "Computer Vision", "Natural Language Processing",
        "Software Architecture", "Distributed Systems", "Operating Systems", "Compiler Design", "Theory of Computation",
        "Algorithm Design", "Database Systems", "Web Technologies", "Mobile Computing", "Game Development",
        "Cloud Platforms", "Network Programming", "Parallel Computing", "Cybersecurity", "Programming Languages",
        "Data Mining", "Big Data", "Human-Computer Interaction", "Robotics", "Bioinformatics",
        "Information Retrieval", "Software Testing", "Embedded Systems", "Graphics Programming", "Quantum Computing"
    ],
    "BSPSY": [
        "Psychological Assessment", "Counseling Skills", "Research Methods", "Clinical Psychology", "Developmental Psychology",
        "Abnormal Psychology", "Social Psychology", "Industrial Psychology", "Educational Psychology", "Statistics",
        "Test Construction", "Interviewing Skills", "Group Dynamics", "Personality Theories", "Cognitive Psychology",
        "Behavior Modification", "Crisis Intervention", "Psychotherapy", "Mental Health Awareness", "Case Management",
        "Report Writing", "Ethics in Psychology", "Community Psychology", "Forensic Psychology", "Neuropsychology",
        "Child Psychology", "Aging and Psychology", "Health Psychology", "Cross-cultural Psychology", "Program Evaluation"
    ],
    "BSCRIM": [
        "Criminal Law", "Forensic Science", "Investigation Techniques", "Criminological Research", "Police Administration",
        "Law Enforcement", "Self-defense", "Firearms Proficiency", "Crime Scene Management", "Court Testimony",
        "Security Management", "Traffic Management", "Correctional Administration", "Juvenile Justice", "Victimology",
        "Cybercrime", "Community Policing", "Human Rights", "Disaster Response", "Drug Education",
        "Report Writing", "Interview and Interrogation", "Fingerprint Analysis", "Ballistics", "Lie Detection",
        "Surveillance", "Evidence Handling", "Legal Procedures", "Crisis Negotiation", "Public Safety"
    ],
    "BSED_MATH": [
        "Algebra", "Geometry", "Trigonometry", "Calculus", "Statistics",
        "Mathematical Proofs", "Number Theory", "Linear Algebra", "Differential Equations", "Math Modeling",
        "Math Lesson Planning", "Classroom Management", "Assessment Design", "Math Technology Tools", "Math Curriculum",
        "Problem Solving", "Math Communication", "Math Research", "Math Remediation", "Math Games",
        "Math History", "Math for Early Grades", "Math for Secondary", "Math for College", "Math in Real Life",
        "Math Project Work", "Math Olympiad Coaching", "Math Anxiety Reduction", "Math Tutoring", "Math Evaluation"
    ],
    "BSED_ENG": [
        "English Grammar", "Literature Analysis", "Creative Writing", "Speech Communication", "Language Assessment",
        "English Lesson Planning", "Classroom Management", "English Curriculum", "Reading Strategies", "Essay Writing",
        "Research Skills", "Public Speaking", "Debate", "Drama", "Linguistics",
        "Phonetics", "Language Acquisition", "English for Academic Purposes", "Technical Writing", "Editing",
        "English for Business", "English for Media", "English for Tourism", "English for Science", "English for Law",
        "English for IT", "English for Social Sciences", "English for Early Grades", "English for Secondary", "English for College"
    ],
    "BSHM": [
        "Front Office Operations", "Housekeeping", "Food and Beverage Service", "Culinary Arts", "Event Management",
        "Hotel Management", "Customer Service", "Bartending", "Baking", "Banquet Operations",
        "Hospitality Marketing", "Tourism Management", "Travel Agency Operations", "Resort Management", "Hospitality Accounting",
        "Hospitality Law", "Hospitality HR", "Hospitality IT", "Hospitality Sales", "Hospitality English",
        "Wine Studies", "Barista Skills", "Menu Planning", "Cost Control", "Sustainable Tourism",
        "Hospitality Entrepreneurship", "Hospitality Research", "Hospitality Training", "Hospitality Safety", "Hospitality Leadership"
    ],
    "BSBM_MKT": [
        "Marketing Research", "Digital Marketing", "Sales Management", "Brand Management", "Consumer Behavior",
        "Advertising", "Retail Management", "Product Management", "Market Analysis", "Strategic Marketing",
        "Public Relations", "Event Marketing", "Social Media Marketing", "Content Creation", "E-commerce",
        "Business Analytics", "Customer Relationship Management", "Pricing Strategies", "Distribution Management", "International Marketing",
        "Marketing Communications", "Market Segmentation", "Marketing Planning", "Marketing Ethics", "Marketing Law",
        "Sales Forecasting", "Trade Marketing", "Channel Management", "B2B Marketing", "Service Marketing"
    ],
    "BSBM_HR": [
        "Recruitment", "Training and Development", "Compensation and Benefits", "Labor Relations", "Performance Management",
        "HR Analytics", "Organizational Development", "Employee Engagement", "HR Policy", "HR Law",
        "HR Information Systems", "Talent Management", "Succession Planning", "Conflict Resolution", "Diversity Management",
        "Change Management", "Workforce Planning", "Job Analysis", "HR Branding", "HR Metrics",
        "Payroll Management", "Employee Relations", "HR Communication", "HR Compliance", "HR Auditing",
        "HR Risk Management", "HR for Startups", "HR for SMEs", "HR for Large Enterprises", "HR Project Management"
    ],
}

class Command(BaseCommand):
    help = 'Seeds the database with only official CVSU Bacoor Campus courses, advisers, and 30 real skills per course.'

    def handle(self, *args, **options):
        User = get_user_model()
        valid_codes = set(course["code"] for course in COURSES)
        # Delete courses not in the official list
        deleted_courses, _ = Course.objects.exclude(code__in=valid_codes).delete()
        # Delete all previous skills to avoid unique constraint errors
        deleted_skills, _ = Skill.objects.all().delete()
        created = 0
        for course in COURSES:
            course_obj, was_created = Course.objects.get_or_create(
                code=course["code"],
                defaults={
                    "name": course["name"],
                    "required_ojt_hours": course["required_ojt_hours"]
                }
            )
            if was_created:
                created += 1
            # Ensure at least one adviser per course
            adviser_email = f"adviser_{course_obj.code.lower()}@cvsu.edu.ph"
            adviser_user, _ = User.objects.get_or_create(
                email=adviser_email,
                defaults={
                    "username": f"adviser_{course_obj.code.lower()}",
                    "first_name": "Default",
                    "last_name": f"Adviser {course_obj.code}",
                    "user_type": "ADVISER",
                    "is_active": True
                }
            )
            adviser_profile, _ = AdviserProfile.objects.get_or_create(
                user=adviser_user,
                defaults={"department": "OJT Department"}
            )
            adviser_profile.courses.add(course_obj)
            # Set default password for adviser if just created
            if _:
                adviser_user.set_password('password123')
                adviser_user.save()
            # Add 30 real, unique skills (append course code to ensure uniqueness)
            for skill_name in SKILLS[course_obj.code][:30]:
                unique_skill_name = f"{skill_name} ({course_obj.code})"
                Skill.objects.create(name=unique_skill_name, course=course_obj)
        self.stdout.write(self.style.SUCCESS(f"{created} courses added. Non-official courses deleted: {deleted_courses}. All previous skills deleted: {deleted_skills}. Advisers and 30 unique skills per course ensured. Default password for all advisers: password123"))
