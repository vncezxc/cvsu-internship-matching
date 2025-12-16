from django.shortcuts import render

from accounts.models import StudentProfile, User
from internship.models import Company

def home(request):
    # Count currently active students (User is_active=True and user_type=STUDENT)
    students_placed_count = User.objects.filter(is_active=True, user_type=User.UserType.STUDENT).count()
    # Count all companies in the system
    company_count = Company.objects.all().count()
    return render(request, 'home.html', {
        'students_placed_count': students_placed_count,
        'company_count': company_count,
    })
