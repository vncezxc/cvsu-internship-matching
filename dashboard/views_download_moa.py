import os
from django.http import FileResponse, Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from accounts.models import RequiredDocument, StudentDocument
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.text import slugify
import requests
import io




@login_required
def download_edited_required_document(request, doc_id):
    """Download document template (coordinator only)"""
    if not request.user.is_coordinator:
        raise Http404("Permission denied")
    
    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    if not required_doc.template_file:
        raise Http404("Document template not found")
    
    try:
        # For storage backends that support direct download
        if hasattr(required_doc.template_file, 'url'):
            # Get the file from storage
            file_obj = required_doc.template_file
            
            # Generate filename
            original_name = file_obj.name
            base_name = os.path.splitext(os.path.basename(original_name))[0]
            filename = f"{slugify(base_name)}_template.docx"
            
            # Try to get file content directly
            if hasattr(file_obj, 'read'):
                # FileField supports read()
                file_content = file_obj.read()
                response = HttpResponse(file_content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                # Fallback: redirect to URL
                return redirect(file_obj.url)
        
        # Fallback to direct download
        file_path = required_doc.template_file.path
        if os.path.exists(file_path):
            return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
        
    except Exception as e:
        print(f"Error downloading file: {e}")
    
    raise Http404("Document not available for download")


@login_required
def download_edited_moa(request, doc_id):
    """Download MOA (students get their copy, coordinators get template)"""
    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    
    # Determine which file to download
    if request.user.is_student:
        # Get student's specific document
        student_doc = StudentDocument.objects.filter(
            student=request.user.student_profile,
            required_document=required_doc
        ).first()
        
        if student_doc and student_doc.file:
            file_to_download = student_doc.file
            filename = f"moa_{slugify(request.user.get_full_name())}_{slugify(required_doc.name)}.docx"
        else:
            # Fallback to template
            file_to_download = required_doc.template_file
            filename = f"moa_template_{slugify(required_doc.name)}.docx"
            
    elif request.user.is_coordinator:
        # Coordinators get the template
        file_to_download = required_doc.template_file
        filename = f"moa_template_{slugify(required_doc.name)}.docx"
        
    else:
        raise Http404("Permission denied")
    
    if not file_to_download:
        raise Http404("MOA template not found")
    
    try:
        # Handle different storage backends
        if hasattr(file_to_download, 'url'):
            # For storage backends with URL access
            if hasattr(file_to_download, 'read'):
                # Read directly from storage
                file_content = file_to_download.read()
                response = HttpResponse(
                    file_content,
                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                # Redirect to the file URL
                return redirect(file_to_download.url)
        
        # Local file fallback
        file_path = file_to_download.path
        if os.path.exists(file_path):
            return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
        
    except Exception as e:
        print(f"Error downloading MOA: {e}")
        # Last resort: try to download via URL
        if hasattr(file_to_download, 'url'):
            try:
                response = requests.get(file_to_download.url)
                if response.status_code == 200:
                    file_content = io.BytesIO(response.content)
                    return FileResponse(file_content, as_attachment=True, filename=filename)
            except:
                pass
    
    raise Http404("MOA not available for download")


@login_required
def download_moa_direct(request, doc_id):
    """Direct download with redirect to file URL (for large files)"""
    required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    
    if request.user.is_student:
        student_doc = StudentDocument.objects.filter(
            student=request.user.student_profile,
            required_document=required_doc
        ).first()
        
        if student_doc and student_doc.file:
            file_url = student_doc.file.url
        else:
            file_url = required_doc.template_file.url
    else:
        file_url = required_doc.template_file.url
    
    if not file_url:
        raise Http404("File not found")
    
    # Redirect to the file URL (let the storage service handle the download)
    return redirect(file_url)