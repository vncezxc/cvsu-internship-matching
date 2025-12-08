from django.urls import path, include
from . import views
from . import views_resend_verification
from .profile_views import adviser_profile_view, coordinator_profile_view

app_name = 'accounts'

urlpatterns = [
    # Profile views
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/<int:user_id>/', views.profile_view, name='profile_by_id'),  # New URL pattern for student profile view by user id
    path('adviser/profile/', adviser_profile_view, name='adviser_profile'),
    path('coordinator/profile/', coordinator_profile_view, name='coordinator_profile'),
   
    # Document management
    path('documents/', views.document_list, name='document_list'),
    path('documents/upload/', views.upload_document, name='upload_document'),
    path('documents/<int:document_id>/delete/', views.delete_document, name='delete_document'),
    
    # CV management
    path('cv/upload/', views.upload_cv, name='upload_cv'),
    path('cv/delete/', views.delete_cv, name='delete_cv'),
    
    # Skills management
    path('skills/', views.manage_skills, {'course_id': None}, name='manage_skills'),
    path('skills/add/', views.add_skill, {'course_id': None}, name='add_skill'),
    path('remove-skill/<int:skill_id>/', views.remove_skill, name='remove_skill'),  # URL pattern for removing skills
    
    # Location management
    path('location/', views.update_location, name='update_location'),

    # User management
    path('users/', views.user_list, name='user_list'),

    # Adviser course management
    path('manage-courses/', views.manage_courses, name='manage_courses'),
    path('add-course/', views.add_course, name='add_course'),
    path('edit-course/<int:course_id>/', views.edit_course, name='edit_course'),
    path('delete-course/<int:course_id>/', views.delete_course, name='delete_course'),

    # Adviser skill management
    path('manage-skills/<int:course_id>/', views.manage_skills, name='manage_skills'),
    path('add-skill/<int:course_id>/', views.add_skill, name='add_skill'),
    path('edit-skill/<int:course_id>/<int:skill_id>/', views.edit_skill, name='edit_skill'),
    path('delete-skill/<int:course_id>/<int:skill_id>/', views.delete_skill, name='delete_skill'),

    # Registration views
    path('register/student/', views.student_register, name='student_register'),
    path('register/adviser/', views.adviser_register, name='adviser_register'),
    path('register/coordinator/', views.coordinator_register, name='coordinator_register'),
    path('register/', views.register_choice, name='register_choice'),
    # OJT status update
    path('update-ojt-status/', views.update_ojt_status, name='update_ojt_status'),
    
    # AllAuth authentication URLs
     path('verify-email-code/', views.verify_email_code, name='verify_email_code'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('', include('allauth.urls')),
]