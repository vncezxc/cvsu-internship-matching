from django.core.management.base import BaseCommand
from accounts.models import Course, Skill

class Command(BaseCommand):
    help = 'Seed 30 skills per course if not already present.'

    def handle(self, *args, **options):
        for course in Course.objects.all():
            existing = Skill.objects.filter(course=course).count()
            to_create = 30 - existing
            for i in range(1, to_create + 1):
                Skill.objects.get_or_create(name=f"{course.code} Skill {existing + i}", course=course)
            self.stdout.write(self.style.SUCCESS(f"Ensured 30 skills for course {course.code}"))
