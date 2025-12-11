import jwt
import datetime
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import RequiredDocument
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import requests

logger = logging.getLogger(__name__)

def get_absolute_file_url(file_field):
    """
    Get absolute URL for a file that OnlyOffice can access.
    Handles Cloudinary URLs and local media files.
    """
    if not file_field:
        return ""
    
    url = file_field.url
    
    # If already a full URL (Cloudinary)
    if url.startswith('http'):
        return url
    
    # For production (Render)
    if not settings.DEBUG:
        base_url = getattr(settings, 'BASE_URL', 'https://cvsu-internship-matching.onrender.com')
        # Ensure proper URL format
        if url.startswith('/'):
            return f"{base_url}{url}"
        else:
            return f"{base_url}/{url}"
    
    # For local development
    return url

def get_jwt_token(payload):
    """Safely generate JWT token with error handling"""
    if not hasattr(settings, 'ONLYOFFICE_SECRET') or not settings.ONLYOFFICE_SECRET:
        logger.error("ONLYOFFICE_SECRET is not configured")
        return ""
    
    try:
        token = jwt.encode(payload, settings.ONLYOFFICE_SECRET, algorithm="HS256")
        # Handle bytes/string conversion (PyJWT 2.0+ returns string)
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return token
    except Exception as e:
        logger.error(f"JWT generation failed: {e}")
        return ""

def test_onlyoffice_connection():
    """Test if OnlyOffice server is accessible"""
    if not hasattr(settings, 'ONLYOFFICE_URL') or not settings.ONLYOFFICE_URL:
        return False, "ONLYOFFICE_URL not configured"
    
    try:
        # Remove trailing slash for healthcheck
        base_url = settings.ONLYOFFICE_URL.rstrip('/')
        response = requests.get(f"{base_url}/healthcheck", timeout=5)
        if response.status_code == 200 and response.text.strip().lower() == 'true':
            return True, "Connected"
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused. Check if OnlyOffice server is running."
    except Exception as e:
        return False, str(e)

@login_required
@csrf_exempt
def edit_required_document_full_view(request, doc_id):
    """View for coordinators to edit documents"""
    
    # Test OnlyOffice connection
    connected, message = test_onlyoffice_connection()
    if not connected:
        messages.error(request, f'OnlyOffice server is not accessible: {message}')
        logger.error(f"OnlyOffice connection failed: {message}")
        return redirect('dashboard:required_documents_list')
    
    # Only coordinators can access
    if not request.user.is_coordinator:
        messages.error(request, 'You do not have permission to edit this document.')
        return redirect('dashboard:required_documents_list')

    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    if not required_doc.template_file:
        messages.error(request, 'No template uploaded for this document.')
        return redirect('dashboard:required_documents_list')
    
    # Check if it's a DOCX file
    filename = str(required_doc.template_file).lower()
    if not filename.endswith('.docx'):
        messages.error(request, 'Only DOCX files are supported for editing.')
        return redirect('dashboard:required_documents_list')

    # Get absolute file URL
    docx_url = get_absolute_file_url(required_doc.template_file)
    
    if not docx_url:
        messages.error(request, 'Could not generate document URL.')
        return redirect('dashboard:required_documents_list')
    
    # Generate unique key with timestamp
    from django.utils.timezone import now
    document_key = f"req_doc_{required_doc.id}_{now().timestamp()}"

    # Generate JWT token
    base_url = getattr(settings, 'BASE_URL', 'https://cvsu-internship-matching.onrender.com')
    callback_url = f"{base_url}/dashboard/required-documents/{doc_id}/onlyoffice-callback/"
    
    payload = {
        "document": {
            "fileType": "docx",
            "key": document_key,
            "title": required_doc.name[:50],  # Limit title length
            "url": docx_url
        },
        "editorConfig": {
            "mode": "edit",
            "lang": "en",
            "callbackUrl": callback_url,
            "customization": {
                "autosave": True,
                "comments": True,
                "compactToolbar": False
            }
        },
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    
    token = get_jwt_token(payload)
    if not token:
        messages.error(request, 'Failed to generate security token. Check server configuration.')
        return redirect('dashboard:required_documents_list')

    context = {
        'required_doc': required_doc,
        'docx_url': docx_url,
        'token': token,
        'onlyoffice_url': settings.ONLYOFFICE_URL.rstrip('/'),  # Remove trailing slash
        'editor_mode': 'edit',
        'connection_status': f"✅ Connected to OnlyOffice" if connected else f"❌ {message}",
        'debug_mode': settings.DEBUG,
    }
    
    logger.info(f"Rendering OnlyOffice editor for document {doc_id}, URL: {docx_url}")
    return render(request, 'dashboard/edit_moa.html', context)

@login_required
def edit_moa_view(request, doc_id):
    """View for students/coordinators to edit MOA"""
    
    # Test OnlyOffice connection
    connected, message = test_onlyoffice_connection()
    if not connected:
        messages.error(request, f'OnlyOffice server is not accessible: {message}')
        return redirect('dashboard:student_documents')
    
    # Only students and coordinators can access
    if not (request.user.is_student or request.user.is_coordinator):
        messages.error(request, 'You do not have permission to edit the MOA.')
        return redirect('dashboard:student_documents')

    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    if not required_doc.template_file:
        messages.error(request, 'No MOA template uploaded.')
        return redirect('dashboard:student_documents')
    
    # Check if it's a DOCX file
    filename = str(required_doc.template_file).lower()
    if not filename.endswith('.docx'):
        messages.error(request, 'Only DOCX files are supported for MOA editing.')
        return redirect('dashboard:student_documents')

    # Get absolute file URL (always use template on production)
    docx_url = get_absolute_file_url(required_doc.template_file)
    
    if not docx_url:
        messages.error(request, 'Could not generate document URL.')
        return redirect('dashboard:student_documents')
    
    # Generate unique key
    from django.utils.timezone import now
    document_key = f"user_{request.user.id}_moa_{now().timestamp()}"
    
    # Determine editor mode
    editor_mode = "edit" if request.user.is_coordinator else "formFilling"
    
    # JWT token
    payload = {
        "document": {
            "fileType": "docx",
            "key": document_key,
            "title": f"{required_doc.name} - {request.user.get_full_name()}"[:60],
            "url": docx_url
        },
        "editorConfig": {
            "mode": editor_mode,
            "lang": "en",
            "callbackUrl": "",  # Empty for now
            "customization": {
                "autosave": True,
                "comments": editor_mode == "edit",
                "compactToolbar": False
            }
        },
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    
    token = get_jwt_token(payload)
    if not token:
        messages.error(request, 'Failed to generate security token.')
        return redirect('dashboard:student_documents')

    context = {
        'required_doc': required_doc,
        'docx_url': docx_url,
        'token': token,
        'editor_mode': editor_mode,
        'onlyoffice_url': settings.ONLYOFFICE_URL.rstrip('/'),
        'connection_status': f"✅ Connected to OnlyOffice" if connected else f"❌ {message}",
        'debug_mode': settings.DEBUG,
    }
    return render(request, 'dashboard/edit_moa.html', context)