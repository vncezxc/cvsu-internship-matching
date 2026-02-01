from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from .views import send_verification_code  # Import the code sender function

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
    
    # Send 6-digit verification code instead of link
    success = send_verification_code(user)
    
    if success:
        # Store user info in session for verification page
        request.session['verifying_user_id'] = user.id
        request.session['verifying_user_email'] = user.email
        request.session['verification_session_time'] = str(user.date_joined)
        
        return JsonResponse({
            'success': True, 
            'message': 'A verification code has been sent to your email.',
            'redirect_url': '/accounts/verify-email-code/'
        })
    else:
        return JsonResponse({'success': False, 'message': 'Failed to send verification code. Please try again.'})

