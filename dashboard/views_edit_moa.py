import jwt
import datetime
# Generalized CKEditor editor view for any required document with a DOCX template



import io
import os
import mammoth
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
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
        'page': 1,
        'total_pages': 1,
    }
    return render(request, 'dashboard/edit_moa.html', context)

# Utility: extract paragraphs for a given page and build a temp DOCX, then convert to HTML
def extract_docx_page_html(docx_path, page_idx, markers):
    # Split the doc into pages (list of list of block elements: paragraphs and tables)
    doc = Document(docx_path)
    body = doc.element.body
    blocks = []
    for child in body.iterchildren():
        if child.tag == qn('w:p'):
            blocks.append(('p', child))
        elif child.tag == qn('w:tbl'):
            blocks.append(('tbl', child))
    pages = []
    current_page = []
    marker_idx = 0
    marker_count = len(markers)
    for block_type, block in blocks:
        if block_type == 'p':
            # Get text for marker detection
            para_text = ''
            for node in block.iter():
                if node.tag == qn('w:t'):
                    para_text += node.text or ''
            current_page.append(('p', block))
            if marker_idx < marker_count and markers[marker_idx] in para_text.strip():
                if current_page:
                    pages.append(current_page)
                current_page = []
                marker_idx += 1
        elif block_type == 'tbl':
            current_page.append(('tbl', block))
    if current_page:
        pages.append(current_page)
    # Clamp page_idx
    if page_idx < 1:
        page_idx = 1
    if page_idx > len(pages):
        page_idx = len(pages)
    # Build a temp DOCX for the selected page, preserving paragraphs and tables
    temp_doc = Document()
    # Remove default empty paragraph
    temp_doc._body.clear_content()
    for block_type, block in pages[page_idx-1]:
        # Import the XML element directly into the new document's body
        temp_doc._body._element.append(block)
    # Save to BytesIO
    temp_stream = io.BytesIO()
    temp_doc.save(temp_stream)
    temp_stream.seek(0)
    # Convert to HTML
    result = mammoth.convert_to_html(temp_stream)
    html = result.value
    return html, len(pages)

def extract_docx_full_html(docx_path):
    """Extract DOCX as HTML with formatting using mammoth only."""
    try:
        with open(docx_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html = result.value
            if html.strip():
                return html
    except Exception:
        pass
    # Fallback to plain text if all else fails
    doc = Document(docx_path)
    return '<br>'.join([p.text for p in doc.paragraphs])

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
    html_output_path = os.path.join(settings.MEDIA_ROOT, f"user_{request.user.id}_moa.html")

    # Custom page markers provided by the user (exact text)
    markers = [
        'd.\tProvide free medical and dental services and certification by a duly licensed medical doctor and dentist to the interns;',
        '7.\tTermination. This MOA may be terminated by either Party upon thirty (30) working days written notice to the other Party prior to the effective date of termination on the ground that either Party violated the foregoing covenants and such violation cannot be addressed by the appropriate corrective measures.',
        'd.\tAny activity that involves processing of personal data shall comply with the Data Privacy Act of 2012 (or Republic Act No. 10173), its Implementing Rules and Regulations, and other applicable laws and administrative issuances. The parties shall perform any or all actions necessary to facilitate such processing of personal data, including the execution of contracts, securing of consent, and other similar or related acts.',
        'This attachment lists the names of students enrolled in the internship/on-the-job training program as per the Memorandum of Agreement between Cavite State University and [Name of HTE] dated [insert original date of MOA].'
    ]

    # Determine which page to show
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # Coordinator: OnlyOffice integration
    if request.user.is_coordinator or request.user.is_student:
        # Use the original or user-edited DOCX file
        if os.path.exists(output_path):
            docx_url = request.build_absolute_uri(settings.MEDIA_URL + f"user_{request.user.id}_moa.docx")
        else:
            docx_url = request.build_absolute_uri(settings.MEDIA_URL + required_doc.template_file.name)
        # JWT token for OnlyOffice
        onlyoffice_secret = getattr(settings, 'ONLYOFFICE_SECRET', 'your-very-secret-key')
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
            'page': 1,
            'total_pages': 1,
        }
        return render(request, 'dashboard/edit_moa.html', context)

    # Student/Adviser: Inline editing (original logic)
    # Always use the latest edited version if it exists
    if os.path.exists(output_path):
        pages = extract_editable_runs_by_custom_markers(output_path, markers)
    else:
        pages = extract_editable_runs_by_custom_markers(docx_path, markers)

    total_pages = len(pages)
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    if request.method == 'POST':
        # Handle MOA reset (restore original template for any required document)
        if request.POST.get('reset_moa') == '1':
            if os.path.exists(output_path):
                os.remove(output_path)
            messages.success(request, 'Document has been reset to the original coordinator template.')
            return redirect(request.path)

        # Inline editing: get JSON of changes
        import json
        updates = {}
        editable_json = request.POST.get('editable_json')
        if editable_json:
            data = json.loads(editable_json)
            for key, value in data.items():
                if key.startswith('p') and '_r' in key:
                    parts = key[1:].split('_r')
                    para_idx = int(parts[0])
                    run_idx = int(parts[1])
                    updates[(para_idx, run_idx)] = value
        # Always overwrite the edited file with the latest changes
        update_editable_runs_by_page(docx_path, updates, output_path)
        messages.success(request, f'Document page {page} updated successfully!')
        # Stay on the same page after save
        return redirect(f"{request.path}?page={page}")

    # Re-extract the current page after any update
    if os.path.exists(output_path):
        pages = extract_editable_runs_by_custom_markers(output_path, markers)
    else:
        pages = extract_editable_runs_by_custom_markers(docx_path, markers)

    context = {
        'required_doc': required_doc,
        'page_data': pages[page-1] if pages else [],
        'page': page,
        'total_pages': total_pages,
    }
    return render(request, 'dashboard/edit_moa.html', context)
