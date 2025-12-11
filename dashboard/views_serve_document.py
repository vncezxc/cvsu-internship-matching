import jwt
import os
import mimetypes
from django.http import FileResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from accounts.models import RequiredDocument


@csrf_exempt
def serve_document_for_onlyoffice(request, doc_id):
    """
    Proxy endpoint for OnlyOffice DocumentServer to access files
    without triggering browser downloads or CORS issues.
    """
    try:
        required_doc = get_object_or_404(RequiredDocument, id=doc_id)
    except:
        return HttpResponse('Document not found', status=404)
    
    # Get the file path
    file_path = required_doc.template_file.path
    
    if not os.path.exists(file_path):
        return HttpResponse('File not found on disk', status=404)
    
    # Read file content
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    # Use HttpResponse with binary content for full control over headers
    response = HttpResponse(file_content)
    
    # Set content type to application/octet-stream to prevent browser from treating it as downloadable DOCX
    # OnlyOffice will still recognize it correctly
    response['Content-Type'] = 'application/octet-stream'
    
    # CORS and caching headers for OnlyOffice
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    response['Cache-Control'] = 'no-cache'
    
    return response
