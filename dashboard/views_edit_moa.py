
import jwt
import datetime
import logging
import os
import uuid
import boto3
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
        logger.error("No file_field provided")
        return ""
    
    try:
        from cvsu_internship.settings import get_absolute_media_url
        url = file_field.url
        logger.info(f"File field name: {file_field.name}")
        logger.info(f"File URL from field: {url}")

        # Always use the helper to generate the correct public URL
        abs_url = get_absolute_media_url(file_field.name)
        logger.info(f"✅ Using absolute URL: {abs_url}")
        return abs_url
    except Exception as e:
        logger.error(f"❌ Error getting file URL: {e}", exc_info=True)
        return ""


def get_or_create_editable_document(required_doc, user):
    """Get or create an editable document copy for the user."""
    try:
        if user.is_student:
            # FIXED: Use 'document_type' instead of 'required_document'
            student_doc, created = StudentDocument.objects.get_or_create(
                student=user.student_profile,
                document_type=required_doc,  # ✅ Changed from required_document
                defaults={'status': 'pending'}
            )
            
            if created or not student_doc.file:
                if required_doc.template_file:
                    original_name = required_doc.template_file.name
                    base_name, ext = os.path.splitext(os.path.basename(original_name))
                    new_filename = f"student_profiles/moa_{user.username}_{slugify(base_name)}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                    
                    # Read the template file
                    with required_doc.template_file.open('rb') as source_file:
                        content = source_file.read()
                    
                    # Upload to Spaces with explicit public ACL
                    session = boto3.session.Session()
                    s3 = session.client(
                        's3',
                        region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'sgp1'),
                        endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None),
                        aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                        aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
                    )
                    bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
                    
                    # Guarantee the key never includes the bucket name as a prefix
                    key = new_filename.lstrip('/')
                    bucket_prefixes = [f"{bucket}/", f"/{bucket}/"]
                    for prefix in bucket_prefixes:
                        if key.startswith(prefix):
                            key = key[len(prefix):]

                    logger.info(f"Uploading to S3 Key: {key}")
                    s3.put_object(
                        Bucket=bucket,
                        Key=key,
                        Body=content,
                        ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        ACL='public-read'
                    )

                    # Save just the filename, not the full path
                    student_doc.file.name = key
                    student_doc.save()
                    logger.info(f"✅ Created editable copy for student: {key}")
                    
            return student_doc.file
            
        elif user.is_coordinator:
            return required_doc.template_file
            
    except Exception as e:
        logger.error(f"❌ Error creating editable document: {e}", exc_info=True)
        return required_doc.template_file
    
    return required_doc.template_file


def generate_jwt_payload(document_key, document_url, title, editor_mode="edit", user=None, doc_id=None):
    """Generate JWT payload for OnlyOffice."""
    is_coordinator = user.is_coordinator if user else False
    
    permissions = {
        "edit": True,  # Everyone can edit
        "download": True,
        "print": True,
        "review": True,
        "comment": True,
        "fillForms": True,
        "modifyFilter": is_coordinator,
        "modifyContentControl": True
    }

    if doc_id is None:
        raise ValueError("doc_id must be provided for OnlyOffice callback URL.")
    
    callback_url = f"{getattr(settings, 'BASE_URL', 'https://cvsu-internship-matching.onrender.com')}/dashboard/required-documents/{doc_id}/onlyoffice-callback/"
    
    payload = {
        "document": {
            "fileType": "docx",
            "key": document_key,
            "title": title[:128],
            "url": document_url,
            "permissions": permissions
        },
        "documentType": "word",
        "editorConfig": {
            "mode": "edit",  # Always edit mode
            "lang": "en",
            "callbackUrl": callback_url,
            "customization": {
                "autosave": True,
                "compactToolbar": False,
                "feedback": False,
                "help": False,
                "toolbarNoTabs": False,
                "forcesave": True
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

    editor_mode = "edit"
    document_key = f"{request.user.id}_{doc_id}"

    payload = generate_jwt_payload(
        document_key=document_key,
        document_url=document_url,
        title=f"{required_doc.name} - {request.user.get_full_name()}",
        editor_mode=editor_mode,
        user=request.user,
        doc_id=doc_id
    )
    token = get_jwt_token(payload)
    if not token:
        messages.error(request, "Failed to generate security token.")
        return redirect('dashboard:student_documents')

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



@csrf_exempt
def onlyoffice_callback(request, doc_id):
    """Handle OnlyOffice save callback - NO LOGIN REQUIRED."""
    if request.method != 'POST':
        return JsonResponse({'error': 0})

    try:
        import json
        data = json.loads(request.body)
        status = data.get('status', 0)
        document_key = data.get('key', '')
        
        logger.info(f"OnlyOffice callback: status={status}, key={document_key}, doc_id={doc_id}")

        # Status 2 = document ready to save
        if status == 2:
            url = data.get('url')
            if not url:
                logger.error("No download URL in callback")
                return JsonResponse({'error': 1})

            # Download the edited document from OnlyOffice
            response = requests.get(url, verify=False, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to download from OnlyOffice: {response.status_code}")
                return JsonResponse({'error': 1})

            # Parse document_key to find user type and user_id
            key_parts = document_key.split('_')
            is_coordinator = key_parts[0] == 'coord'
            
            if is_coordinator:
                user_id = int(key_parts[1]) if len(key_parts) > 1 else None
            else:
                user_id = int(key_parts[0]) if len(key_parts) > 0 else None

            if not user_id:
                logger.error(f"Could not parse user_id from key: {document_key}")
                return JsonResponse({'error': 1})

            # Get the user and required document
            try:
                from accounts.models import User
                user = User.objects.get(id=user_id)
                required_doc = RequiredDocument.objects.get(id=doc_id)
            except (User.DoesNotExist, RequiredDocument.DoesNotExist) as e:
                logger.error(f"User or document not found: {e}")
                return JsonResponse({'error': 1})

            # Setup S3/Spaces connection
            session = boto3.session.Session()
            s3 = session.client(
                's3',
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'sgp1'),
                endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None),
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
            )
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)

            if is_coordinator:
                # COORDINATOR: Update template file
                original_name = required_doc.template_file.name
                base_name, ext = os.path.splitext(os.path.basename(original_name))
                new_filename = f"document_templates/template_{slugify(base_name)}_v{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

                # Guarantee the key never includes the bucket name as a prefix
                key = new_filename.lstrip('/')
                bucket_prefixes = [f"{bucket}/", f"/{bucket}/"]
                for prefix in bucket_prefixes:
                    if key.startswith(prefix):
                        key = key[len(prefix):]

                logger.info(f"Uploading to S3 Key: {key}")
                s3.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=response.content,
                    ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    ACL='public-read'
                )

                required_doc.template_file.name = key
                required_doc.save()
                logger.info(f"✅ Updated template for doc {doc_id} by coordinator {user.username}")

            else:
                # STUDENT: Update student document
                try:
                    student_profile = user.student_profile
                    student_doc = StudentDocument.objects.filter(
                        student=student_profile,
                        document_type=required_doc
                    ).first()

                    if student_doc:
                        original_name = required_doc.template_file.name
                        base_name, ext = os.path.splitext(os.path.basename(original_name))
                        new_filename = f"student_profiles/moa_{user.username}_{slugify(base_name)}_edited_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

                        # Guarantee the key never includes the bucket name as a prefix
                        key = new_filename.lstrip('/')
                        bucket_prefixes = [f"{bucket}/", f"/{bucket}/"]
                        for prefix in bucket_prefixes:
                            if key.startswith(prefix):
                                key = key[len(prefix):]

                        logger.info(f"Uploading to S3 Key: {key}")
                        s3.put_object(
                            Bucket=bucket,
                            Key=key,
                            Body=response.content,
                            ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                            ACL='public-read'
                        )

                        student_doc.file.name = key
                        student_doc.status = 'submitted'
                        student_doc.save()
                        logger.info(f"✅ Saved edited document for student {user.username}")
                    else:
                        logger.error(f"StudentDocument not found for user {user.username}")
                        return JsonResponse({'error': 1})

                except Exception as e:
                    logger.error(f"❌ Error updating student document: {e}", exc_info=True)
                    return JsonResponse({'error': 1})

            return JsonResponse({'error': 0})

        # For other statuses, just acknowledge
        return JsonResponse({'error': 0})

    except Exception as e:
        logger.error(f"❌ OnlyOffice callback error: {e}", exc_info=True)
        return JsonResponse({'error': 1, 'message': str(e)})

@login_required
@csrf_exempt
def edit_required_document_full_view(request, doc_id):
    """View for coordinators to edit the original template."""
    if not request.user.is_coordinator:
        messages.error(request, "You do not have permission to edit this template.")
        return redirect('dashboard:required_documents_list')

    connected, message = test_onlyoffice_connection()
    if not connected:
        messages.error(request, f"OnlyOffice server not accessible: {message}")
        return redirect('dashboard:required_documents_list')

    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    if not required_doc.template_file:
        messages.error(request, "No template uploaded for this document.")
        return redirect('dashboard:required_documents_list')

    document_file = required_doc.template_file
    document_url = get_absolute_file_url(document_file)
    if not document_url:
        messages.error(request, "Could not generate document URL.")
        return redirect('dashboard:required_documents_list')

    document_key = f"coord_{request.user.id}_{doc_id}_{uuid.uuid4().hex}"
    payload = generate_jwt_payload(
        document_key=document_key,
        document_url=document_url,
        title=f"{required_doc.name} (Template)",
        editor_mode="edit",
        user=request.user,
        doc_id=doc_id
    )
    token = get_jwt_token(payload)
    if not token:
        messages.error(request, "Failed to generate security token.")
        return redirect('dashboard:required_documents_list')

    request.session['onlyoffice_document_key'] = document_key
    request.session['onlyoffice_document_id'] = doc_id
    request.session['onlyoffice_user_type'] = 'coordinator'

    context = {
        'required_doc': required_doc,
        'document_url': document_url,
        'document_key': document_key,
        'token': token,
        'editor_mode': 'edit',
        'onlyoffice_url': settings.ONLYOFFICE_URL.rstrip('/'),
        'connection_status': f"✅ Connected" if connected else f"❌ {message}",
        'debug_mode': settings.DEBUG,
    }
    return render(request, 'dashboard/edit_moa.html', context)