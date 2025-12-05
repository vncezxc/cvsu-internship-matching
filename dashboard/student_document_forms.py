from django import forms
from accounts.models import StudentDocument, RequiredDocument

class StudentDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = StudentDocument
        fields = ['document_type', 'file']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['document_type'].widget = forms.HiddenInput()
        self.fields['file'].label = ''
