from django.apps import AppConfig
from django.db.models.signals import post_migrate


SOFT_SKILLS = [
    'Accountability',
    'Adaptability',
    'Analytical Thinking',
    'Attention to Detail',
    'Collaboration',
    'Communication',
    'Conflict Resolution',
    'Creativity',
    'Critical Thinking',
    'Customer Focus',
    'Decision Making',
    'Dependability',
    'Emotional Intelligence',
    'Empathy',
    'Flexibility',
    'Growth Mindset',
    'Initiative',
    'Interpersonal Skills',
    'Leadership',
    'Listening',
    'Negotiation',
    'Organization',
    'Patience',
    'Problem Solving',
    'Professionalism',
    'Public Speaking',
    'Resilience',
    'Responsibility',
    'Self Management',
    'Stress Management',
    'Teamwork',
    'Time Management',
    'Work Ethic',
]

COURSE_SOFT_SKILLS = {
    'BSIT': [
        'Analytical Thinking',
        'Attention to Detail',
        'Collaboration',
        'Communication',
        'Critical Thinking',
        'Problem Solving',
        'Time Management',
    ],
    'BSCS': [
        'Analytical Thinking',
        'Attention to Detail',
        'Collaboration',
        'Critical Thinking',
        'Problem Solving',
        'Resilience',
        'Time Management',
    ],
    'BSHM': [
        'Communication',
        'Customer Focus',
        'Empathy',
        'Flexibility',
        'Professionalism',
        'Teamwork',
        'Time Management',
    ],
    'BSPSY': [
        'Active Listening',
        'Communication',
        'Critical Thinking',
        'Empathy',
        'Emotional Intelligence',
        'Ethics',
        'Professionalism',
    ],
    'BSCRIM': [
        'Accountability',
        'Decision Making',
        'Ethics',
        'Professionalism',
        'Resilience',
        'Stress Management',
        'Teamwork',
    ],
    'BSED_MATH': [
        'Communication',
        'Critical Thinking',
        'Organization',
        'Patience',
        'Professionalism',
        'Public Speaking',
        'Time Management',
    ],
    'BSED_ENG': [
        'Communication',
        'Creativity',
        'Organization',
        'Patience',
        'Professionalism',
        'Public Speaking',
        'Time Management',
    ],
    'BSBM_MKT': [
        'Communication',
        'Creativity',
        'Negotiation',
        'Problem Solving',
        'Professionalism',
        'Public Speaking',
        'Teamwork',
    ],
    'BSBM_HR': [
        'Communication',
        'Conflict Resolution',
        'Empathy',
        'Negotiation',
        'Professionalism',
        'Teamwork',
        'Time Management',
    ],
}


def seed_soft_skills(sender, **kwargs):
    from .models import Skill, Course
    for name in SOFT_SKILLS:
        Skill.objects.get_or_create(name=name, course=None)
    courses = {course.code: course for course in Course.objects.all()}
    for course_code, skills in COURSE_SOFT_SKILLS.items():
        course = courses.get(course_code)
        if not course:
            continue
        for name in skills:
            Skill.objects.get_or_create(name=name)


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        post_migrate.connect(seed_soft_skills, sender=self, dispatch_uid='accounts_seed_soft_skills')
