from django.urls import path
from . import views

app_name = 'internship'

urlpatterns = [
    # Student views
    path('matches/', views.internship_matches, name='matches'),
    path('applications/', views.application_history, name='applications'),
    path('apply/<int:internship_id>/', views.apply_internship, name='apply'),
    path('company/<int:company_id>/', views.company_detail, name='company_detail'),
    path('company/<int:company_id>/review/', views.add_company_review, name='add_review'),
    
    # Coordinator views
    path('companies/', views.company_list, name='companies'),
    path('companies/add/', views.add_company, name='add_company'),
    path('companies/<int:company_id>/edit/', views.edit_company, name='edit_company'),
    path('companies/<int:company_id>/toggle-status/', views.toggle_company_status, name='toggle_company_status'),
    
    path('internships/', views.internship_list, name='internships'),
    path('internships/add/', views.add_internship, name='add_internship'),
    path('internships/<int:internship_id>/', views.internship_detail, name='internship_detail'),
    path('internships/<int:internship_id>/edit/', views.edit_internship, name='edit_internship'),
    path('internships/<int:internship_id>/toggle-status/', views.toggle_internship_status, name='toggle_internship_status'),
    path('internships/<int:internship_id>/delete/', views.delete_internship, name='delete_internship'),
    
    # API endpoints for AJAX
    path('api/skills/by-course/<int:course_id>/', views.api_skills_by_course, name='api_skills_by_course'),
    
    # Application detail view
    path('applications/<int:application_id>/', views.application_detail, name='application_detail'),
]