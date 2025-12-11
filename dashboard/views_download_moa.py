from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from accounts.models import RequiredDocument
from django.conf import settings
import requests
import io


@login_required
def download_edited_required_document(request, doc_id):
    """Download edited document (coordinator only)"""
    if not request.user.is_coordinator:
        raise Http404("Permission denied")
    
    # In production, you should implement proper file storage
    # For now, return the original template
    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    if not required_doc.template_file:
        raise Http404("Document not found")
    
    # For Cloudinary files
    if hasattr(required_doc.template_file, 'url'):
        # Download file from Cloudinary
        try:
            response = requests.get(required_doc.template_file.url)
            if response.status_code == 200:
                file_content = io.BytesIO(response.content)
                filename = f"required_doc_{doc_id}_template.docx"
                return FileResponse(file_content, as_attachment=True, filename=filename)
        except:
            pass
    
    raise Http404("Document not available for download")

@login_required
def download_edited_moa(request, doc_id):
    """Download MOA (students and coordinators)"""
    if not (request.user.is_student or request.user.is_coordinator):
        raise Http404("Permission denied")
    
    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    if not required_doc.template_file:
        raise Http404("MOA template not found")
    
    # In production, you need to implement document saving via OnlyOffice callbacks
    # For now, return the original template
    if hasattr(required_doc.template_file, 'url'):
        try:
            response = requests.get(required_doc.template_file.url)
            if response.status_code == 200:
                file_content = io.BytesIO(response.content)
                filename = f"moa_{request.user.get_full_name().replace(' ', '_')}.docx"
                return FileResponse(file_content, as_attachment=True, filename=filename)
        except Exception as e:
            print(f"Error downloading file: {e}")
    
    raise Http404("MOA not available for download")