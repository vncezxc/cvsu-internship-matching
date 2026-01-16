
import jwt
import datetime
import logging
import os
import uuid
import boto3
from urllib.parse import quote
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import RequiredDocument, StudentDocument
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.text import slugify
import requests
from django.http import JsonResponse, HttpResponse

logger = logging.getLogger(__name__)


def get_absolute_file_url(file_field):
    """Get absolute URL for a file OnlyOffice can access."""
    if not file_field:
        logger.error("No file_field provided")
        return ""
    
    try:
        url = file_field.url

        # Log what we're working with
        logger.info(f"File field name: {file_field.name}")
        logger.info(f"File URL from field: {url}")

        # If already a full URL from Spaces, use it directly
        if url.startswith('http://') or url.startswith('https://'):
            logger.info(f"✅ Using absolute URL: {url}")
            return url

        # For production, use the CDN domain
        if not settings.DEBUG:
            cdn_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)
            
            if cdn_domain:
                # Remove duplicate bucket prefix if present
                file_path = file_field.name.strip().lstrip('/')
                bucket = settings.AWS_STORAGE_BUCKET_NAME
                
                if file_path.startswith(f"{bucket}/"):
                    file_path = file_path[len(f"{bucket}/"):]
                
                full_url = f"https://{cdn_domain}/{file_path}"
                logger.info(f"✅ Constructed CDN URL: {full_url}")
                return full_url
            else:
                # Fallback to direct Spaces URL
                region = settings.AWS_S3_REGION_NAME
                bucket = settings.AWS_STORAGE_BUCKET_NAME
                file_path = file_field.name.strip().lstrip('/')
                
                if file_path.startswith(f"{bucket}/"):
                    file_path = file_path[len(f"{bucket}/"):]
                
                full_url = f"https://{bucket}.{region}.digitaloceanspaces.com/{file_path}"
                logger.info(f"✅ Constructed Spaces URL: {full_url}")
                return full_url

        # Local development
        local_url = f"http://localhost:8000{url if url.startswith('/') else '/' + url}"
        logger.info(f"✅ Using local URL: {local_url}")
        return local_url

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
                    # Use the same filename as the template, but in the student_profiles folder
                    base_name, ext = os.path.splitext(os.path.basename(original_name))
                    new_filename = f"student_profiles/moa_{user.username}_{slugify(base_name)}{ext}"
                    
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
                    

                    # Ensure key does not start with the bucket name
                    key = new_filename.lstrip('/')
                    if key.startswith(f"{bucket}/"):
                        key = key[len(f"{bucket}/"):]

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


def get_proxy_url(file_field):
    """Return proxy URL that streams the file via our domain for OnlyOffice."""
    try:
        name = getattr(file_field, 'name', None)
        if not name:
            logger.error("Proxy URL: file_field has no name")
            return ""
        base = getattr(settings, 'BASE_URL', '').rstrip('/')
        proxied = f"{base}/dashboard/onlyoffice/file-proxy/?path={quote(name)}"
        logger.info(f"✅ Using proxy URL for OnlyOffice: {proxied}")
        return proxied
    except Exception as e:
        logger.error(f"❌ Error building proxy URL: {e}", exc_info=True)
        return ""


@require_http_methods(["GET", "HEAD"])
def onlyoffice_file_proxy(request):
    """Proxy endpoint: streams document to OnlyOffice from CDN/Spaces.
    Supports GET and HEAD, sets appropriate headers.
    """
    path = request.GET.get('path', '')
    if not path:
        return JsonResponse({'error': 'missing path'}, status=400)

    # Build absolute source URL using settings helper when needed
    try:
        if path.startswith(('http://', 'https://')):
            source_url = path
        else:
            # settings.get_absolute_media_url handles AWS_LOCATION/CDN
            source_url = settings.get_absolute_media_url(path)

        upstream = requests.request(request.method, source_url, stream=True, verify=False, timeout=30)
        if upstream.status_code != 200:
            logger.error(f"Proxy upstream error {upstream.status_code} for {source_url}")
            return HttpResponse(status=upstream.status_code)

        content_type = upstream.headers.get('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        filename = os.path.basename(path)

        if request.method == 'HEAD':
            resp = HttpResponse('', status=200)
            resp['Content-Length'] = upstream.headers.get('Content-Length', '0')
        else:
            content = upstream.content
            resp = HttpResponse(content, content_type=content_type)
            resp['Content-Length'] = upstream.headers.get('Content-Length', str(len(content)))

        resp['Accept-Ranges'] = 'bytes'
        resp['Content-Disposition'] = f'inline; filename="{filename}"'
        resp['Cache-Control'] = 'no-cache'
        return resp
    except Exception as e:
        logger.error(f"❌ Proxy error: {e}", exc_info=True)
        return HttpResponse(status=500)


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
    # Use proxy URL so OnlyOffice fetches via our domain
    document_url = get_proxy_url(document_file)
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
                # Use the same filename as the template, in the document_templates folder
                base_name, ext = os.path.splitext(os.path.basename(original_name))
                new_filename = f"document_templates/template_{slugify(base_name)}{ext}"


                # Ensure key does not start with the bucket name
                key = new_filename.lstrip('/')
                if key.startswith(f"{bucket}/"):
                    key = key[len(f"{bucket}/"):]

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
                        # Use the same filename as the template, but in the student_profiles folder
                        base_name, ext = os.path.splitext(os.path.basename(original_name))
                        new_filename = f"student_profiles/moa_{user.username}_{slugify(base_name)}{ext}"


                        # Ensure key does not start with the bucket name
                        key = new_filename.lstrip('/')
                        if key.startswith(f"{bucket}/"):
                            key = key[len(f"{bucket}/"):]

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
    # Use proxy URL so OnlyOffice fetches via our domain
    document_url = get_proxy_url(document_file)
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