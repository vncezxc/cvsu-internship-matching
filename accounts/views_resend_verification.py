from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST

@csrf_exempt
@require_POST
def resend_verification_public(request):
    email = request.POST.get('email')
    if not email:
        return JsonResponse({'success': False, 'message': 'Email is required.'})
    User = get_user_model()
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'No user found with this email.'})
    email_address = EmailAddress.objects.filter(user=user, email=email).first()
    if email_address and email_address.verified:
        return JsonResponse({'success': False, 'message': 'This email is already verified.'})
    send_email_confirmation(request, user, signup=False)
    return JsonResponse({'success': True, 'message': 'A new verification email has been sent.'})
