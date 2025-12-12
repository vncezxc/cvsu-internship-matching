import jwt
import datetime
import logging
import os
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import RequiredDocument, StudentDocument
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.text import slugify
import requests
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def get_absolute_file_url(file_field):
    """Get absolute URL for a file OnlyOffice can access."""
    if not file_field:
        return ""
    try:
        url = file_field.url
        if url.startswith('http'):
            return url
        if not settings.DEBUG:
            base_url = getattr(settings, 'BASE_URL', 'https://cvsu-internship-matching.onrender.com')
            if url.startswith('/'):
                return f"{base_url}{url}"
            else:
                return f"{base_url}/{url}"
        return f"http://localhost:8000{url}"
    except Exception as e:
        logger.error(f"Error getting file URL: {e}")
        return ""


def get_or_create_editable_document(required_doc, user):
    """Get or create an editable document copy for the user."""
    try:
        if user.is_student:
            student_doc, created = StudentDocument.objects.get_or_create(
                student=user.student_profile,
                required_document=required_doc,
                defaults={'status': 'pending', 'document_type': 'moa'}
            )
            if created or not student_doc.file:
                if required_doc.template_file:
                    original_name = required_doc.template_file.name
                    base_name, ext = os.path.splitext(os.path.basename(original_name))
                    new_filename = f"moa_{user.username}_{slugify(base_name)}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                    with required_doc.template_file.open('rb') as source_file:
                        student_doc.file.save(new_filename, source_file, save=True)
                    logger.info(f"Created editable copy for student: {new_filename}")
            return student_doc.file
        elif user.is_coordinator:
            return required_doc.template_file
    except Exception as e:
        logger.error(f"Error creating editable document: {e}")
        return required_doc.template_file
    return required_doc.template_file


def generate_jwt_payload(document_key, document_url, title, editor_mode="edit", user=None):
    """Generate JWT payload for OnlyOffice."""
    permissions = {
        "edit": True,
        "download": True,
        "print": True,
        "review": True,
        "comment": True,
        "fillForms": True
    }

    payload = {
        "document": {
            "fileType": "docx",
            "key": document_key,
            "title": title[:128],
            "url": document_url,
            "permissions": permissions
        },
        "editorConfig": {
            "mode": editor_mode,
            "lang": "en",
            "callbackUrl": "https://cvsu-internship-matching.onrender.com/dashboard/onlyoffice-callback/",
            "customization": {
                "autosave": True,
                "compactToolbar": False,
                "feedback": False,
                "help": False,
                "toolbarNoTabs": False
            },
            "user": {
                "id": str(user.id) if user else "anonymous",
                "name": user.get_full_name() if user else "Anonymous"
            }
        }
    }
    return payload


def get_jwt_token(payload):
    """Generate JWT token."""
    secret = getattr(settings, 'ONLYOFFICE_SECRET', None)
    if not secret:
        logger.error("ONLYOFFICE_SECRET is not configured")
        return ""
    try:
        token = jwt.encode(payload, secret, algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return token
    except Exception as e:
        logger.error(f"JWT generation failed: {e}")
        return ""


def test_onlyoffice_connection():
    """Test OnlyOffice server connection."""
    url = getattr(settings, 'ONLYOFFICE_URL', None)
    if not url:
        return False, "ONLYOFFICE_URL not configured"
    try:
        response = requests.get(f"{url.rstrip('/')}/healthcheck", timeout=5, verify=False)
        if response.status_code == 200:
            return True, "Connected"
        return False, f"HTTP {response.status_code}: {response.reason}"
    except Exception as e:
        return False, str(e)


@login_required
@csrf_exempt
def edit_moa_view(request, doc_id):
    """
    View for students and coordinators to edit MOA.
    Coordinators get full edit; students get formFilling.
    """
    connected, message = test_onlyoffice_connection()
    if not connected:
        messages.error(request, f"OnlyOffice server not accessible: {message}")
        return redirect('dashboard:student_documents')

    if not (request.user.is_student or request.user.is_coordinator):
        messages.error(request, "You do not have permission to edit this document.")
        return redirect('dashboard:student_documents')

    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    if not required_doc.template_file:
        messages.error(request, "No MOA template available.")
        return redirect('dashboard:student_documents')

    document_file = get_or_create_editable_document(required_doc, request.user)
    document_url = get_absolute_file_url(document_file)
    if not document_url:
        messages.error(request, "Could not generate document URL.")
        return redirect('dashboard:student_documents')

    # Editor mode
    editor_mode = "edit" if request.user.is_coordinator else "formFilling"

    # Stable document key per user per document
    document_key = f"{request.user.id}_{doc_id}"

    payload = generate_jwt_payload(
        document_key=document_key,
        document_url=document_url,
        title=f"{required_doc.name} - {request.user.get_full_name()}",
        editor_mode=editor_mode,
        user=request.user
    )
    token = get_jwt_token(payload)
    if not token:
        messages.error(request, "Failed to generate security token.")
        return redirect('dashboard:student_documents')

    # Store in session
    request.session['onlyoffice_document_key'] = document_key
    request.session['onlyoffice_document_id'] = doc_id
    request.session['onlyoffice_user_type'] = 'coordinator' if request.user.is_coordinator else 'student'

    context = {
        'required_doc': required_doc,
        'document_url': document_url,
        'document_key': document_key,
        'token': token,
        'editor_mode': editor_mode,
        'onlyoffice_url': settings.ONLYOFFICE_URL.rstrip('/'),
        'connection_status': f"✅ Connected" if connected else f"❌ {message}",
        'debug_mode': settings.DEBUG,
    }
    return render(request, 'dashboard/edit_moa.html', context)


@login_required
@csrf_exempt
def onlyoffice_callback(request):
    """Handle OnlyOffice save callback."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        import json
        data = json.loads(request.body)
        status = data.get('status', 0)
        document_key = data.get('key')

        if status == 2 and document_key:
            url = data.get('url')
            if url:
                response = requests.get(url, verify=False)
                if response.status_code == 200:
                    doc_id = request.session.get('onlyoffice_document_id')
                    user_type = request.session.get('onlyoffice_user_type')
                    required_doc = get_object_or_404(RequiredDocument, id=doc_id)

                    if user_type == 'student':
                        student_doc = StudentDocument.objects.filter(
                            student=request.user.student_profile,
                            required_document=required_doc
                        ).first()
                        if student_doc:
                            original_name = required_doc.template_file.name
                            base_name, ext = os.path.splitext(os.path.basename(original_name))
                            new_filename = f"moa_{request.user.username}_{slugify(base_name)}_edited_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                            student_doc.file.save(new_filename, response.content, save=True)
                            student_doc.status = 'submitted'
                            student_doc.save()
                            logger.info(f"Saved edited document for student {request.user.username}")

                    elif user_type == 'coordinator':
                        original_name = required_doc.template_file.name
                        base_name, ext = os.path.splitext(os.path.basename(original_name))
                        new_filename = f"template_{slugify(base_name)}_v{datetime.datetime.now().strftime('%Y%m%d')}{ext}"
                        required_doc.template_file.save(new_filename, response.content, save=True)
                        logger.info(f"Updated template for document {doc_id} by coordinator {request.user.username}")

        return JsonResponse({'error': 0})

    except Exception as e:
        logger.error(f"OnlyOffice callback error: {e}")
        return JsonResponse({'error': 1, 'message': str(e)})
