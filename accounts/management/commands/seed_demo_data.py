from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import Course, Skill, StudentProfile
from internship.models import Company, Internship


DEMO_COMPANIES = [
    {
        "name": "DEMO TechNova Solutions",
        "description": "A demo technology company for internship matching demonstrations.",
        "company_type": Company.CompanyType.PRIVATE,
        "city": "Bacoor",
        "province": "Cavite",
    },
    {
        "name": "DEMO BrightPath Analytics",
        "description": "A demo data and analytics organization for student showcases.",
        "company_type": Company.CompanyType.PRIVATE,
        "city": "Imus",
        "province": "Cavite",
    },
    {
        "name": "DEMO Community Care Center",
        "description": "A demo community organization for social science and psychology placements.",
        "company_type": Company.CompanyType.NGO,
        "city": "Dasmarinas",
        "province": "Cavite",
    },
    {
        "name": "DEMO Civic Services Office",
        "description": "A demo government office for public service related internship flows.",
        "company_type": Company.CompanyType.GOVERNMENT,
        "city": "Trece Martires",
        "province": "Cavite",
    },
    {
        "name": "DEMO Campus Learning Hub",
        "description": "A demo academic partner for teaching and education related practice teaching support.",
        "company_type": Company.CompanyType.ACADEMIC,
        "city": "General Trias",
        "province": "Cavite",
    },
]


class Command(BaseCommand):
    help = (
        "Seed demonstration data: sample companies, internships, and student accounts "
        "for every course. Safe to run multiple times."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--students-per-course",
            type=int,
            default=2,
            help="How many demo students to create per course (default: 2).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        students_per_course = max(1, options["students_per_course"])

        courses = list(Course.objects.order_by("code"))
        if not courses:
            self.stdout.write(
                self.style.WARNING(
                    "No courses found. Run `python manage.py seed_courses` first, then run this command again."
                )
            )
            return

        created_companies, updated_companies = self._seed_companies()
        created_internships, updated_internships = self._seed_internships(courses)
        created_users, created_profiles, updated_profiles = self._seed_students(
            courses, students_per_course
        )

        self.stdout.write(self.style.SUCCESS("Demo data seeding completed."))
        self.stdout.write(
            f"Companies: {created_companies} created, {updated_companies} updated"
        )
        self.stdout.write(
            f"Internships: {created_internships} created, {updated_internships} updated"
        )
        self.stdout.write(
            f"Student users: {created_users} created"
        )
        self.stdout.write(
            f"Student profiles: {created_profiles} created, {updated_profiles} updated"
        )
        self.stdout.write(
            self.style.WARNING(
                "Default demo password for seeded students: DemoPass123!"
            )
        )

    def _seed_companies(self):
        User = get_user_model()
        coordinator = (
            User.objects.filter(user_type=User.UserType.COORDINATOR, is_active=True)
            .order_by("id")
            .first()
        )

        created = 0
        updated = 0

        for index, company_data in enumerate(DEMO_COMPANIES, start=1):
            defaults = {
                "description": company_data["description"],
                "company_type": company_data["company_type"],
                "company_email": f"demo.company{index}@cvsu.edu.ph",
                "hr_email": f"demo.hr{index}@cvsu.edu.ph",
                "phone_number": f"09170000{index:03d}",
                "street": f"{index} Demo Avenue",
                "barangay": "Demo Barangay",
                "city": company_data["city"],
                "province": company_data["province"],
                "status": Company.Status.ACTIVE,
                "approval_status": Company.ApprovalStatus.APPROVED,
                "added_by": coordinator,
            }

            company, was_created = Company.objects.get_or_create(
                name=company_data["name"],
                defaults=defaults,
            )

            if was_created:
                created += 1
            else:
                changed = False
                for field, value in defaults.items():
                    if getattr(company, field) != value:
                        setattr(company, field, value)
                        changed = True
                if changed:
                    company.save()
                    updated += 1

        return created, updated

    def _seed_internships(self, courses):
        companies = list(Company.objects.filter(name__startswith="DEMO ").order_by("id"))
        if not companies:
            return 0, 0

        created = 0
        updated = 0

        internship_titles = [
            "Internship - Applied Practice",
            "Internship - Operations Support",
            "Internship - Project Assistant",
            "Internship - Field Exposure",
            "Internship - Research Support",
        ]

        for idx, course in enumerate(courses):
            company = companies[idx % len(companies)]
            title = f"{course.code} {internship_titles[idx % len(internship_titles)]}"
            description = (
                f"Demo internship for {course.name}. This posting exists for presentations and system demos."
            )

            internship, was_created = Internship.objects.get_or_create(
                company=company,
                title=title,
                defaults={
                    "description": description,
                    "is_active": True,
                    "slots_available": 5,
                    "approval_status": Internship.ApprovalStatus.APPROVED,
                },
            )

            if was_created:
                created += 1
            else:
                changed = False
                if internship.description != description:
                    internship.description = description
                    changed = True
                if internship.slots_available != 5:
                    internship.slots_available = 5
                    changed = True
                if internship.is_active is not True:
                    internship.is_active = True
                    changed = True
                if internship.approval_status != Internship.ApprovalStatus.APPROVED:
                    internship.approval_status = Internship.ApprovalStatus.APPROVED
                    changed = True
                if changed:
                    internship.save()
                    updated += 1

            internship.recommended_courses.set([course])
            skill_qs = Skill.objects.filter(course=course).order_by("id")[:3]
            internship.required_skills.set(skill_qs)

        return created, updated

    def _seed_students(self, courses, students_per_course):
        User = get_user_model()
        created_users = 0
        created_profiles = 0
        updated_profiles = 0

        for course in courses:
            course_skills = list(Skill.objects.filter(course=course).order_by("id")[:5])

            for number in range(1, students_per_course + 1):
                username = f"demo_{course.code.lower()}_{number:02d}"
                email = f"{username}@cvsu.edu.ph"
                student_id = f"DEMO-{course.code}-{number:03d}"

                user, was_created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": username,
                        "first_name": f"Demo{number}",
                        "last_name": course.code,
                        "user_type": User.UserType.STUDENT,
                        "is_active": True,
                    },
                )

                if was_created:
                    user.set_password("DemoPass123!")
                    user.save()
                    created_users += 1
                elif user.user_type != User.UserType.STUDENT:
                    user.user_type = User.UserType.STUDENT
                    user.save(update_fields=["user_type"])

                profile, profile_created = StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "student_id": student_id,
                        "course": course,
                        "year_level": StudentProfile.YearLevel.FOURTH,
                        "section": "A",
                        "phone_number": f"09990000{number:03d}",
                        "street": "Demo Street",
                        "barangay": "Demo Barangay",
                        "city": "Bacoor",
                        "province": "Cavite",
                        "ojt_status": StudentProfile.OJTStatus.LOOKING,
                    },
                )

                if profile_created:
                    created_profiles += 1
                else:
                    changed = False
                    if profile.course_id != course.id:
                        profile.course = course
                        changed = True
                    if not profile.student_id:
                        profile.student_id = student_id
                        changed = True
                    if not profile.section:
                        profile.section = "A"
                        changed = True
                    if not profile.city:
                        profile.city = "Bacoor"
                        changed = True
                    if not profile.province:
                        profile.province = "Cavite"
                        changed = True
                    if changed:
                        profile.save()
                        updated_profiles += 1

                if course_skills:
                    profile.skills.set(course_skills)

        return created_users, created_profiles, updated_profiles
