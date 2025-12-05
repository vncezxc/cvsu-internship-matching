from django.http import HttpResponse, FileResponse

# Download the full edited required document (HTML version)
from django.contrib.auth.decorators import login_required
import os
from django.conf import settings
from accounts.models import RequiredDocument

@login_required
def download_edited_required_document(request, doc_id):
    # Only coordinators can access
    if not request.user.is_coordinator:
        raise Http404()
    docx_output_path = os.path.join(settings.MEDIA_ROOT, f"required_doc_{doc_id}_edited.docx")
    if not os.path.exists(docx_output_path):
        raise Http404("Edited document not found.")
    return FileResponse(open(docx_output_path, 'rb'), as_attachment=True, filename=f'required_doc_{doc_id}_edited.docx')
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required
import os
from django.conf import settings
from accounts.models import RequiredDocument

@login_required
def download_edited_moa(request, doc_id):
    # Only students and coordinators can access
    if not (request.user.is_student or request.user.is_coordinator):
        raise Http404()
    # Path where the edited MOA is saved
    filename = f"user_{request.user.id}_moa.docx"
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    if not os.path.exists(file_path):
        raise Http404("Edited MOA not found.")
    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
