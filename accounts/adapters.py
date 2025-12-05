from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
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