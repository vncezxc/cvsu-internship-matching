from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import AdviserProfile, CoordinatorProfile

@login_required
def adviser_profile_view(request):
    try:
        profile = request.user.adviser_profile
    except (AttributeError, AdviserProfile.DoesNotExist):
        messages.warning(request, 'Please complete your adviser profile.')
        return redirect('accounts:edit_profile')
    return render(request, 'accounts/adviser_profile.html', {'profile': profile})

@login_required
def coordinator_profile_view(request):
    try:
        profile = request.user.coordinator_profile
    except (AttributeError, CoordinatorProfile.DoesNotExist):
        messages.warning(request, 'Please complete your coordinator profile.')
        return redirect('accounts:edit_profile')
    return render(request, 'accounts/coordinator_profile.html', {'profile': profile})
