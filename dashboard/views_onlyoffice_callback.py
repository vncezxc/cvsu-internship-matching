import os
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings

@csrf_exempt
def onlyoffice_callback(request, doc_id):
    """
    Receives OnlyOffice callback with edited document and saves it to MEDIA_ROOT.
    """
    if request.method == "POST":
        import json
        data = json.loads(request.body.decode())
        print(f"ONLYOFFICE CALLBACK: Received data for doc_id={doc_id}: {data}")
        status = data.get("status")
        # Only save if status == 2 (document is ready for saving)
        if status == 2:
            download_url = data.get("url")
            print(f"ONLYOFFICE CALLBACK: Download URL: {download_url}")
            if download_url:
                import requests
                response = requests.get(download_url)
                print(f"ONLYOFFICE CALLBACK: Download response status: {response.status_code}")
                if response.status_code == 200:
                    output_path = os.path.join(settings.MEDIA_ROOT, f"required_doc_{doc_id}_edited.docx")
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    print(f"ONLYOFFICE CALLBACK: Saved file to {output_path}, size={len(response.content)} bytes")
                    return JsonResponse({"error": 0})
                else:
                    print(f"ONLYOFFICE CALLBACK: Failed to download file from OnlyOffice.")
        else:
            print(f"ONLYOFFICE CALLBACK: Status is not 2, not saving. Status={status}")
        return JsonResponse({"error": 1, "message": "No document to save."})
    print("ONLYOFFICE CALLBACK: Invalid request method.")
    return JsonResponse({"error": 1, "message": "Invalid request method."})
