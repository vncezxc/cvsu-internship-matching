from django.core.management.base import BaseCommand
from accounts.models import Course, Skill
import json
import os


class Command(BaseCommand):
    help = 'Load courses and skills from db.json'

    def handle(self, *args, **kwargs):
        # Path to db.json
        json_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'db.json')
        
        if not os.path.exists(json_file):
            self.stdout.write(self.style.ERROR(f'db.json not found at {json_file}'))
            return
        
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Load courses
        courses_created = 0
        courses_updated = 0
        
        for item in data:
            if item['model'] == 'accounts.course':
                course_id = item['pk']
                fields = item['fields']
                
                course, created = Course.objects.update_or_create(
                    id=course_id,
                    defaults={
                        'code': fields['code'],
                        'name': fields['name'],
                        'required_ojt_hours': fields['required_ojt_hours'],
                        'description': fields.get('description', '')
                    }
                )
                
                if created:
                    courses_created += 1
                    self.stdout.write(self.style.SUCCESS(f'Created course: {course.code} - {course.name}'))
                else:
                    courses_updated += 1
                    self.stdout.write(self.style.WARNING(f'Updated course: {course.code} - {course.name}'))
        
        # Load skills
        skills_created = 0
        skills_updated = 0
        
        for item in data:
            if item['model'] == 'accounts.skill':
                skill_id = item['pk']
                fields = item['fields']
                
                # Get course if it exists
                course = None
                if fields.get('course'):
                    try:
                        course = Course.objects.get(id=fields['course'])
                    except Course.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'Course {fields["course"]} not found for skill {fields["name"]}'))
                
                skill, created = Skill.objects.update_or_create(
                    id=skill_id,
                    defaults={
                        'name': fields['name'],
                        'course': course
                    }
                )
                
                if created:
                    skills_created += 1
                else:
                    skills_updated += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Completed!'
            f'\nCourses: {courses_created} created, {courses_updated} updated'
            f'\nSkills: {skills_created} created, {skills_updated} updated'
        ))
