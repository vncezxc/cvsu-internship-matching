
from django import forms
from accounts.models import StudentDocument

class StudentDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = StudentDocument
        fields = ['file']

from accounts.models import DTR

class DTRSubmissionForm(forms.ModelForm):
    class Meta:
        model = DTR
        fields = ['week_start', 'week_end', 'file', 'hours_rendered']
        widgets = {
            'week_start': forms.DateInput(attrs={'type': 'date'}),
            'week_end': forms.DateInput(attrs={'type': 'date'}),
        }
        help_texts = {
            'file': 'Upload a PDF or image of your DTR for the week.'
        }
from accounts.models import RequiredDocument

class RequiredDocumentForm(forms.ModelForm):
    class Meta:
        model = RequiredDocument
        fields = ['name', 'description', 'is_required', 'template_file']
