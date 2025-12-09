import jwt
import datetime
import io
import os
import mammoth
import logging
from docx import Document
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import RequiredDocument, StudentDocument
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


@login_required
@csrf_exempt
def edit_required_document_full_view(request, doc_id):
    # Temporary debugging - check what OnlyOffice URL is being used
    logger.warning("ONLYOFFICE_URL runtime value: %s", settings.ONLYOFFICE_URL)
    logger.warning("ONLYOFFICE_SECRET present? %s", bool(settings.ONLYOFFICE_SECRET))
    
    # Only coordinators can access
    if not request.user.is_coordinator:
        messages.error(request, 'You do not have permission to edit this document.')
        return redirect('dashboard:required_documents_list')

    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    if not required_doc.template_file or not str(required_doc.template_file).lower().endswith('.docx'):
        messages.error(request, 'No DOCX template uploaded for this document.')
        return redirect('dashboard:required_documents_list')

    # Build DOCX file URL for OnlyOffice
    docx_url = request.build_absolute_uri(required_doc.template_file.url)

    # Generate JWT token for OnlyOffice
    callback_url = request.build_absolute_uri(f"/dashboard/required-documents/{doc_id}/onlyoffice-callback/")
    payload = {
        "document": {
            "fileType": "docx",
            "key": f"req_doc_{required_doc.id}",
            "title": required_doc.name,
            "url": docx_url
        },
        "editorConfig": {
            "mode": "edit",
            "lang": "en",
            "callbackUrl": callback_url
        },
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.ONLYOFFICE_SECRET, algorithm="HS256")

    context = {
        'required_doc': required_doc,
        'docx_url': docx_url,
        'token': token,
        'onlyoffice_url': settings.ONLYOFFICE_URL,
        'editor_mode': 'edit',
        'page': 1,
        'total_pages': 1,
    }
    return render(request, 'dashboard/edit_moa.html', context)


@login_required
def edit_moa_view(request, doc_id):
    # Only students and coordinators can access
    if not (request.user.is_student or request.user.is_coordinator):
        messages.error(request, 'You do not have permission to edit the MOA.')
        return redirect('dashboard:student_documents')

    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    if not required_doc.template_file:
        messages.error(request, 'No MOA template uploaded.')
        return redirect('dashboard:student_documents')

    # Define path for user's edited version of the document
    output_filename = f"user_{request.user.id}_moa.docx"
    output_path = os.path.join(settings.MEDIA_ROOT, output_filename)

    # Determine which file URL to use for the editor
    if os.path.exists(output_path):
        # If an edited version exists, use it
        document_url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, output_filename))
        document_key = f"user_{request.user.id}_moa_{os.path.getmtime(output_path)}"
    else:
        # Otherwise, use the original template
        document_url = request.build_absolute_uri(required_doc.template_file.url)
        document_key = f"req_doc_{required_doc.id}_template"

    # JWT token for OnlyOffice
    payload = {
        "document": {
            "fileType": "docx",
            "key": document_key,
            "title": required_doc.name,
            "url": document_url
        },
        "editorConfig": {
            "mode": "edit" if request.user.is_coordinator else "formFilling",
            "lang": "en",
            "callbackUrl": ""  # Add callback if needed
        },
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.ONLYOFFICE_SECRET, algorithm="HS256")
    editor_mode = "edit" if request.user.is_coordinator else "formFilling"

    context = {
        'required_doc': required_doc,
        'docx_url': document_url,
        'token': token,
        'editor_mode': editor_mode,
        'onlyoffice_url': settings.ONLYOFFICE_URL,
        'page': 1,
        'total_pages': 1,
    }
    return render(request, 'dashboard/edit_moa.html', context)
