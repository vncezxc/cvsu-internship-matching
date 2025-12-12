import jwt
import datetime
import logging
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import RequiredDocument, StudentDocument
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.utils.text import slugify
import requests
from django.http import JsonResponse

logger = logging.getLogger(__name__)

def get_absolute_file_url(file_field):
    """
    Get absolute URL for a file that OnlyOffice can access.
    Handles Digital Ocean Spaces, Cloudinary URLs, and local media files.
    """
    if not file_field:
        return ""
    
    try:
        # Get URL from the storage backend
        url = file_field.url
        
        # If it's already a full URL (Digital Ocean Spaces, Cloudinary)
        if url.startswith('http'):
            return url
        
        # For local files in production
        if not settings.DEBUG:
            base_url = getattr(settings, 'BASE_URL', 'https://cvsu-internship-matching.onrender.com')
            if url.startswith('/'):
                return f"{base_url}{url}"
            else:
                return f"{base_url}/{url}"
        
        # For local development
        return f"http://localhost:8000{url}"
        
    except Exception as e:
        logger.error(f"Error getting file URL: {e}")
        return ""

def get_or_create_editable_document(required_doc, user):
    """
    Get or create an editable document copy for the user.
    This ensures each user gets their own copy to edit.
    """
    try:
        # Check if student already has a document for this required document
        if user.is_student:
            student_doc, created = StudentDocument.objects.get_or_create(
                student=user.student_profile,
                required_document=required_doc,
                defaults={
                    'status': 'pending',
                    'document_type': 'moa'
                }
            )
            
            # If new or no file exists, copy from template
            if created or not student_doc.file:
                if required_doc.template_file:
                    # Generate unique filename
                    original_name = required_doc.template_file.name
                    base_name, ext = os.path.splitext(os.path.basename(original_name))
                    new_filename = f"moa_{user.username}_{slugify(base_name)}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                    
                    # Copy the file
                    with required_doc.template_file.open('rb') as source_file:
                        student_doc.file.save(new_filename, source_file, save=True)
                    
                    logger.info(f"Created editable copy for student: {new_filename}")
            
            return student_doc.file
        
        # For coordinators, use the template directly
        elif user.is_coordinator:
            return required_doc.template_file
            
    except Exception as e:
        logger.error(f"Error creating editable document: {e}")
        return required_doc.template_file
    
    return required_doc.template_file

def generate_jwt_payload(document_key, document_url, title, editor_mode="edit", user=None):
    """
    Generate JWT payload that OnlyOffice Document Server accepts.
    MUST match the exact structure OnlyOffice expects.
    """
    
    # IMPORTANT: This exact structure (tested and working)
    payload = {
        "document": {
            "fileType": "docx",
            "key": document_key,
            "title": title[:128],
            "url": document_url,
            "permissions": {
                "edit": editor_mode in ["edit", "review", "formFilling"],
                "download": True,
                "print": True,
                "review": editor_mode == "review",
                "comment": True,
                "fillForms": editor_mode == "formFilling",
                "modifyFilter": True,
                "modifyContentControl": True,
                "copy": True,
                "modify": True
            }
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
        # DO NOT include: 'exp', 'token', or any other top-level fields
    }
    
    return payload

def get_jwt_token(payload):
    """Generate JWT token with proper encoding"""
    if not hasattr(settings, 'ONLYOFFICE_SECRET') or not settings.ONLYOFFICE_SECRET:
        logger.error("ONLYOFFICE_SECRET is not configured")
        return ""
    
    try:
        secret = settings.ONLYOFFICE_SECRET
        
        # CRITICAL: Ensure secret matches
        expected_secret = "NfOfVmap1M6BA01YoRX6yeb3kwSHDS"
        if secret != expected_secret:
            logger.error(f"Secret mismatch! Django: {secret}, OnlyOffice: {expected_secret}")
            # Use the correct secret anyway
            secret = expected_secret
        
        # Generate token - payload as-is, NO extra 'exp' field
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        # Handle bytes/string conversion
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        
        logger.info(f"JWT token generated, length: {len(token)}")
        return token
        
    except Exception as e:
        logger.error(f"JWT generation failed: {e}")
        import traceback
        traceback.print_exc()
        return ""

def test_onlyoffice_connection():
    """Test if OnlyOffice server is accessible"""
    if not hasattr(settings, 'ONLYOFFICE_URL') or not settings.ONLYOFFICE_URL:
        return False, "ONLYOFFICE_URL not configured"
    
    try:
        base_url = settings.ONLYOFFICE_URL.rstrip('/')
        # Try healthcheck endpoint
        response = requests.get(f"{base_url}/healthcheck", timeout=5, verify=False)
        if response.status_code == 200:
            return True, "Connected"
        
        # Try main page as fallback
        response = requests.get(base_url, timeout=5, verify=False)
        if response.status_code == 200:
            return True, "Connected (via main page)"
            
        return False, f"HTTP {response.status_code}: {response.reason}"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused. Check if OnlyOffice server is running."
    except Exception as e:
        return False, str(e)

@login_required
@csrf_exempt
def edit_required_document_full_view(request, doc_id):
    """View for coordinators to edit document templates"""
    
    # Test OnlyOffice connection
    connected, message = test_onlyoffice_connection()
    if not connected:
        messages.error(request, f'OnlyOffice server is not accessible: {message}')
        logger.error(f"OnlyOffice connection failed: {message}")
        return redirect('dashboard:required_documents_list')
    
    # Only coordinators can access
    if not request.user.is_coordinator:
        messages.error(request, 'You do not have permission to edit document templates.')
        return redirect('dashboard:required_documents_list')

    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    if not required_doc.template_file:
        messages.error(request, 'No template uploaded for this document.')
        return redirect('dashboard:required_documents_list')
    
    # Check if it's a DOCX file
    filename = str(required_doc.template_file.name).lower()
    allowed_extensions = ['.docx', '.doc', '.odt', '.rtf', '.txt']
    file_ext = os.path.splitext(filename)[1]
    
    if file_ext not in allowed_extensions:
        messages.error(request, f'Only document files are supported for editing. Supported formats: {", ".join(allowed_extensions)}')
        return redirect('dashboard:required_documents_list')
    
    # Get the document to edit (for coordinators, use template directly)
    document_file = required_doc.template_file
    
    # Get absolute file URL
    document_url = get_absolute_file_url(document_file)
    
    if not document_url:
        messages.error(request, 'Could not generate document URL.')
        return redirect('dashboard:required_documents_list')
    
    # Generate unique document key
    from django.utils.timezone import now
    document_key = f"coord_{request.user.id}_doc_{doc_id}_{now().timestamp()}"
    
    # Generate JWT payload
    payload = generate_jwt_payload(
        document_key=document_key,
        document_url=document_url,
        title=f"{required_doc.name} (Template)",
        editor_mode="edit",
        user=request.user
    )
    
    token = get_jwt_token(payload)
    if not token:
        messages.error(request, 'Failed to generate security token. Check server configuration.')
        return redirect('dashboard:required_documents_list')
    
    # Store document key in session for callback
    request.session['onlyoffice_document_key'] = document_key
    request.session['onlyoffice_document_id'] = doc_id
    request.session['onlyoffice_user_type'] = 'coordinator'
    
    context = {
        'required_doc': required_doc,
        'document_url': document_url,
        'document_key': document_key,
        'token': token,
        'onlyoffice_url': settings.ONLYOFFICE_URL.rstrip('/'),
        'editor_mode': 'edit',
        'file_type': file_ext.lstrip('.'),
        'connection_status': f"✅ Connected" if connected else f"❌ {message}",
        'debug_mode': settings.DEBUG,
    }
    
    logger.info(f"Rendering OnlyOffice editor for coordinator {request.user.id}, document {doc_id}")
    return render(request, 'dashboard/edit_moa.html', context)

@login_required
@csrf_exempt
def edit_moa_view(request, doc_id):
    """View for students to edit MOA (fill forms)"""
    
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
        messages.error(request, 'No MOA template available.')
        return redirect('dashboard:student_documents')
    
    # Check if it's a DOCX file
    filename = str(required_doc.template_file.name).lower()
    if not filename.endswith('.docx'):
        messages.warning(request, 'Best editing experience with DOCX files. Other formats may have limited functionality.')
    
    # Get or create editable document for the user
    document_file = get_or_create_editable_document(required_doc, request.user)
    
    if not document_file:
        messages.error(request, 'Could not create editable document.')
        return redirect('dashboard:student_documents')
    
    # Get absolute file URL
    document_url = get_absolute_file_url(document_file)
    
    if not document_url:
        messages.error(request, 'Could not generate document URL.')
        return redirect('dashboard:student_documents')
    
    # Determine editor mode
    if request.user.is_coordinator:
        editor_mode = "edit"  # Coordinators can fully edit
    else:
        editor_mode = "formFilling"  # Students can only fill forms
    
    # Generate unique document key
    from django.utils.timezone import now
    document_key = f"user_{request.user.id}_moa_{doc_id}_{now().timestamp()}"
    
    # Generate JWT payload
    payload = generate_jwt_payload(
        document_key=document_key,
        document_url=document_url,
        title=f"{required_doc.name} - {request.user.get_full_name()}",
        editor_mode=editor_mode,
        user=request.user
    )
    
    token = get_jwt_token(payload)
    if not token:
        messages.error(request, 'Failed to generate security token.')
        return redirect('dashboard:student_documents')
    
    # Store document key in session for callback
    request.session['onlyoffice_document_key'] = document_key
    request.session['onlyoffice_document_id'] = doc_id
    request.session['onlyoffice_user_id'] = request.user.id
    request.session['onlyoffice_user_type'] = 'student' if request.user.is_student else 'coordinator'
    
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
    """Handle OnlyOffice callback for saving documents"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        
        status = data.get('status', 0)
        document_key = data.get('key')
        
        if status == 2:  # Document is ready for saving
            url = data.get('url')
            
            if url and document_key:
                # Download the edited document
                response = requests.get(url, verify=False)
                if response.status_code == 200:
                    # Get original filename from session or generate new one
                    doc_id = request.session.get('onlyoffice_document_id')
                    user_type = request.session.get('onlyoffice_user_type')
                    
                    if doc_id:
                        required_doc = get_object_or_404(RequiredDocument, id=doc_id)
                        
                        if user_type == 'student':
                            # Save to student's document
                            student_doc = StudentDocument.objects.filter(
                                student=request.user.student_profile,
                                required_document=required_doc
                            ).first()
                            
                            if student_doc:
                                # Generate new filename
                                original_name = required_doc.template_file.name
                                base_name, ext = os.path.splitext(os.path.basename(original_name))
                                new_filename = f"moa_{request.user.username}_{slugify(base_name)}_edited_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                                
                                # Save the file
                                student_doc.file.save(new_filename, response.content, save=True)
                                student_doc.status = 'submitted'
                                student_doc.save()
                                
                                logger.info(f"Saved edited document for student {request.user.username}")
                        
                        elif user_type == 'coordinator':
                            # Save as new template version
                            original_name = required_doc.template_file.name
                            base_name, ext = os.path.splitext(os.path.basename(original_name))
                            new_filename = f"template_{slugify(base_name)}_v{datetime.datetime.now().strftime('%Y%m%d')}{ext}"
                            
                            # Save as new file (keep original as backup)
                            required_doc.template_file.save(new_filename, response.content, save=True)
                            
                            logger.info(f"Updated template for document {doc_id} by coordinator {request.user.username}")
                    
                    return JsonResponse({'error': 0})
        
        return JsonResponse({'error': 0})  # Always return success to OnlyOffice
        
    except Exception as e:
        logger.error(f"OnlyOffice callback error: {e}")
        return JsonResponse({'error': 1, 'message': str(e)})