from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from allauth.account.adapter import DefaultAccountAdapter
from accounts.models import StudentProfile, AdviserProfile

class CustomAccountAdapter(DefaultAccountAdapter):
    def is_login_allowed(self, user):
        if not super().is_login_allowed(user):
            return False
        if getattr(user, 'is_student', False):
            try:
                profile = user.student_profile
                if profile.master_list_verification_status == StudentProfile.MasterListVerificationStatus.PENDING:
                    return False
            except StudentProfile.DoesNotExist:
                pass
        return True

    def get_login_redirect_url(self, request):
        user = request.user
        # Student
        if hasattr(user, 'is_student') and user.is_student:
            try:
                profile = user.student_profile
                if not getattr(profile, 'is_complete', lambda: True)():
                    return reverse('accounts:edit_profile')
                return reverse('dashboard:student_dashboard')
            except Exception:
                return reverse('accounts:edit_profile')
        # Adviser
        elif hasattr(user, 'is_adviser') and user.is_adviser:
            try:
                profile = user.adviser_profile
                if not getattr(profile, 'is_complete', lambda: True)():
                    return reverse('accounts:edit_profile')
                return reverse('dashboard:adviser_dashboard')
            except Exception:
                return reverse('accounts:edit_profile')
        # Coordinator
        elif hasattr(user, 'is_coordinator') and user.is_coordinator:
            try:
                profile = user.coordinator_profile
                if not getattr(profile, 'is_complete', lambda: True)():
                    return reverse('accounts:edit_profile')
                return reverse('dashboard:coordinator_dashboard')
            except Exception:
                return reverse('accounts:edit_profile')
        return super().get_login_redirect_url(request)

    def respond_user_inactive(self, request, user):
        if getattr(user, 'is_student', False):
            try:
                profile = user.student_profile
                if profile.master_list_verification_status == StudentProfile.MasterListVerificationStatus.PENDING:
                    has_course = profile.course is not None
                    has_section = bool((profile.section or '').strip())
                    has_adviser = False
                    if has_course and has_section:
                        advisers = AdviserProfile.objects.filter(courses=profile.course)
                        has_adviser = any(profile.section in adviser.get_sections_list() for adviser in advisers)
                    if has_adviser:
                        messages.error(request, 'Your account is pending adviser approval. You can log in after approval.')
                    else:
                        messages.error(request, 'No adviser is assigned for your course/section yet. You can log in after an adviser uploads the master list.')
                    return redirect('account_login')
            except StudentProfile.DoesNotExist:
                pass
        return super().respond_user_inactive(request, user)