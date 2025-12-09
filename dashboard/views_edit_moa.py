import jwt
import datetime
import io
import os
import mammoth
from docx import Document
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import RequiredDocument, StudentDocument
from dashboard.docx_utils import extract_editable_runs, update_editable_runs
from dashboard.docx_utils_page import extract_editable_runs_by_page, update_editable_runs_by_page
from dashboard.docx_utils_custom_page import extract_editable_runs_by_custom_markers
from dashboard.docx_utils_html import extract_docx_page_html, extract_docx_full_html
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


@login_required
@csrf_exempt
def edit_required_document_full_view(request, doc_id):
    # Only coordinators can access
    if not request.user.is_coordinator:
        messages.error(request, 'You do not have permission to edit this document.')
        return redirect('dashboard:required_documents_list')

    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    if not required_doc.template_file or not str(required_doc.template_file).lower().endswith('.docx'):
        messages.error(request, 'No DOCX template uploaded for this document.')
        return redirect('dashboard:required_documents_list')

    # Build DOCX file URL for OnlyOffice
    docx_url = request.build_absolute_uri(settings.MEDIA_URL + required_doc.template_file.name)

    # Generate JWT token for OnlyOffice
    onlyoffice_secret = getattr(settings, 'ONLYOFFICE_SECRET', 'your-very-secret-key')
    onlyoffice_url = getattr(settings, 'ONLYOFFICE_URL', 'http://localhost/') # Get the URL from settings
    callback_url = request.build_absolute_uri(f"/dashboard/required-documents/{doc_id}/onlyoffice-callback/")
    payload = {
        "document": {
            "fileType": "docx",
            "key": str(required_doc.id),
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
    token = jwt.encode(payload, onlyoffice_secret, algorithm="HS256")

    context = {
        'required_doc': required_doc,
        'docx_url': docx_url,
        'token': token,
        'onlyoffice_url': onlyoffice_url, # Pass the URL to the template
        'editor_mode': 'edit', # Explicitly set editor mode for the template
        'page': 1,
        'total_pages': 1,
    }
    return render(request, 'dashboard/edit_moa.html', context)

# Utility: extract paragraphs for a given page and build a temp DOCX, then convert to HTML
def extract_docx_page_html(docx_path, page_idx, markers):
    # ... (This function remains unchanged)
    pass

def extract_docx_full_html(docx_path):
    # ... (This function remains unchanged)
    pass

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

    docx_path = os.path.join(settings.MEDIA_ROOT, required_doc.template_file.name)
    output_path = os.path.join(settings.MEDIA_ROOT, f"user_{request.user.id}_moa.docx")
    
    # Coordinator or Student: OnlyOffice integration
    if request.user.is_coordinator or request.user.is_student:
        # Use the original or user-edited DOCX file
        if os.path.exists(output_path):
            docx_url = request.build_absolute_uri(settings.MEDIA_URL + f"user_{request.user.id}_moa.docx")
        else:
            docx_url = request.build_absolute_uri(settings.MEDIA_URL + required_doc.template_file.name)
            
        # JWT token for OnlyOffice
        onlyoffice_secret = getattr(settings, 'ONLYOFFICE_SECRET', 'your-very-secret-key')
        onlyoffice_url = getattr(settings, 'ONLYOFFICE_URL', 'http://localhost/') # Get the URL from settings
        
        payload = {
            "document": {
                "fileType": "docx",
                "key": str(required_doc.id),
                "title": required_doc.name,
                "url": docx_url
            },
            "editorConfig": {
                "mode": "edit" if request.user.is_coordinator else "formFilling",
                "lang": "en",
                "callbackUrl": ""  # Add callback if needed
            },
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        token = jwt.encode(payload, onlyoffice_secret, algorithm="HS256")
        editor_mode = "edit" if request.user.is_coordinator else "formFilling"
        
        # Use the original or user-edited DOCX file, but after reset always use original
        if os.path.exists(output_path) and not (request.method == 'POST' and request.POST.get('reset_moa') == '1'):
            docx_url_final = request.build_absolute_uri(settings.MEDIA_URL + f"user_{request.user.id}_moa.docx")
        else:
            docx_url_final = request.build_absolute_uri(settings.MEDIA_URL + required_doc.template_file.name)
            
        context = {
            'required_doc': required_doc,
            'docx_url': docx_url_final,
            'token': token,
            'editor_mode': editor_mode,
            'onlyoffice_url': onlyoffice_url, # Pass the URL to the template
            'page': 1,
            'total_pages': 1,
        }
        return render(request, 'dashboard/edit_moa.html', context)

    # Fallback logic (if any) can go here, but your current logic covers all users
    # This part of the code will likely not be reached if a user is a student or coordinator
    messages.error(request, 'An unexpected error occurred.')
    return redirect('dashboard:home')
