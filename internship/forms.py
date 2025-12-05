from django import forms
from .models import Company, CompanyReview, Internship, Skill, Course, Application

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name', 'description', 'company_email', 'hr_email', 'phone_number',
            'company_type',
            'street', 'barangay', 'city', 'province',
            'status', 'has_incentives', 'incentives_details', 'logo', 'location_link', 'banner_image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'company_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'company_type': forms.Select(attrs={'class': 'form-select'}),
            'hr_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'street': forms.TextInput(attrs={'class': 'form-control'}),
            'barangay': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'has_incentives': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incentives_details': forms.Textarea(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'location_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Paste or auto-generate a map link'}),
            'banner_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class CompanyReviewForm(forms.ModelForm):
    class Meta:
        model = CompanyReview
        fields = ['rating', 'comment', 'is_anonymous']
        widgets = {
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'comment': forms.Textarea(attrs={'class': 'form-control'}),
            'is_anonymous': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class InternshipForm(forms.ModelForm):
    recommended_courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'recommended-courses'}),
        required=False,
        label='Recommended Courses'
    )
    required_skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'required-skills'}),
        required=False,
        label='Required Skills'
    )
    free_skills = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Add required skills (comma separated)'}),
        label='Add Custom Skills'
    )
    slots_available = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Slots Available',
        required=True
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Active'
    )

    class Meta:
        model = Internship
        fields = ['company', 'title', 'description', 'recommended_courses', 'required_skills', 'free_skills', 'slots_available', 'is_active']
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'slots_available': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        free_skills = cleaned_data.get('free_skills')
        if free_skills:
            # Split by comma and strip whitespace
            skills = [s.strip() for s in free_skills.split(',') if s.strip()]
            # Add new skills to the Skill model if they don't exist
            for skill_name in skills:
                skill_obj, created = Skill.objects.get_or_create(name=skill_name)
                if 'required_skills' in cleaned_data and cleaned_data['required_skills']:
                    cleaned_data['required_skills'] = list(cleaned_data['required_skills']) + [skill_obj]
                else:
                    cleaned_data['required_skills'] = [skill_obj]
        # Error handling for slots_available
        slots = cleaned_data.get('slots_available')
        if slots is None or slots < 1:
            self.add_error('slots_available', 'Please enter a valid number of slots (at least 1).')
        return cleaned_data

class ApplicationStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'})
        }
