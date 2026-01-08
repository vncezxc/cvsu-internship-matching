from django import forms
from .models import StudentProfile, AdviserProfile, CoordinatorProfile, Skill, Course, RequiredDocument, StudentDocument
from internship.models import Internship
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CourseChoices:
    BSIT = 'BSIT'
    BSCS = 'BSCS'
    BSPSY = 'BSPSY'
    BSCRIM = 'BSCRIM'
    BSED_MATH = 'BSED_MATH'
    BSED_ENG = 'BSED_ENG'
    BSHM = 'BSHM'
    BSBM_MKT = 'BSBM_MKT'
    BSBM_HR = 'BSBM_HR'
    CHOICES = [
        (BSIT, 'Bachelor of Science in Information Technology'),
        (BSCS, 'Bachelor of Science in Computer Science'),
        (BSPSY, 'Bachelor of Science in Psychology'),
        (BSCRIM, 'Bachelor of Science in Criminology'),
        (BSED_MATH, 'Bachelor of Secondary Education (Math)'),
        (BSED_ENG, 'Bachelor of Secondary Education (English)'),
        (BSHM, 'Bachelor of Science in Hospitality Management'),
        (BSBM_MKT, 'BS in Business Management (Marketing)'),
        (BSBM_HR, 'BS in Business Management (Human Resources)'),
    ]

class StudentProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    course = forms.ModelChoiceField(queryset=Course.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input skill-checkbox'}),
        required=False
    )
    class Meta:
        model = StudentProfile
        fields = [
            'student_id', 'first_name', 'last_name', 'email',
            'phone_number', 'street', 'barangay', 'city', 'province',
            'section', 'course', 'year_level', 'skills', 'cv', 'latitude', 'longitude', 'profile_image',
        ]
        labels = {
            'student_id': 'Student ID',
        }
        widgets = {
            'student_id': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'street': forms.TextInput(attrs={'class': 'form-control'}),
            'barangay': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'section': forms.TextInput(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'year_level': forms.Select(attrs={'class': 'form-select'}),
            'cv': forms.FileInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'street': forms.TextInput(attrs={'class': 'form-control'}),
            'barangay': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'section': forms.TextInput(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'year_level': forms.Select(attrs={'class': 'form-select'}),
            'cv': forms.FileInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def clean_student_id(self):
        """Validate that student ID contains only numbers."""
        student_id = self.cleaned_data.get('student_id', '')
        if student_id and not student_id.isdigit():
            raise forms.ValidationError('Student ID must contain only numbers.')
        return student_id

    def clean_first_name(self):
        """Validate that first name contains only letters and spaces."""
        first_name = self.cleaned_data.get('first_name', '')
        if first_name and not all(c.isalpha() or c.isspace() or c == '-' for c in first_name):
            raise forms.ValidationError('First name must contain only letters, spaces, and hyphens.')
        return first_name

    def clean_last_name(self):
        """Validate that last name contains only letters and spaces."""
        last_name = self.cleaned_data.get('last_name', '')
        if last_name and not all(c.isalpha() or c.isspace() or c == '-' for c in last_name):
            raise forms.ValidationError('Last name must contain only letters, spaces, and hyphens.')
        return last_name

    def clean_phone_number(self):
        """Validate that phone number contains only numbers, spaces, hyphens, and plus sign."""
        import re
        phone_number = self.cleaned_data.get('phone_number', '')
        if phone_number:
            # Allow only digits, spaces, hyphens, and plus sign
            if not re.match(r'^[\d\s\-\+]+$', phone_number):
                raise forms.ValidationError('Phone number must contain only numbers, spaces, hyphens, and + sign.')
        return phone_number

    def clean_section(self):
        """Validate that section follows the format like 3-1, 4-2."""
        import re
        section = self.cleaned_data.get('section', '')
        if section:
            # Format: digit(s)-digit(s), e.g., 3-1, 4-2
            if not re.match(r'^\d+-\d+$', section):
                raise forms.ValidationError('Section must follow the format like "3-1", "4-2", etc.')
        return section

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        # Ensure student_id is updated from the form
        profile.student_id = self.cleaned_data.get('student_id', profile.student_id)
        if commit:
            user.save()
            # Reload user from DB to ensure all changes are reflected
            profile.user = User.objects.get(pk=user.pk)
            profile.save()
            self.save_m2m()
        return profile

    class Media:
        js = ('js/skills_autoload.js',)

class AdviserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    year_levels = forms.ChoiceField(
        choices=[('1', '1st Year'), ('2', '2nd Year'), ('3', '3rd Year'), ('4', '4th Year'), ('5', '5th Year')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label='Year Level Handled',
    )
    class Meta:
        model = AdviserProfile
        fields = [
            'first_name', 'last_name', 'email',
            'profile_image', 'phone_number', 'department', 'office', 'year_levels', 'courses', 'sections',
        ]
        widgets = {
            'courses': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
        # If instance exists, set year_levels initial value
        if self.instance and self.instance.year_levels:
            self.initial['year_levels'] = self.instance.year_levels

    def clean_year_levels(self):
        return self.cleaned_data['year_levels']

    def clean_phone_number(self):
        """Validate that phone number contains only numbers, spaces, hyphens, and plus sign."""
        import re
        phone_number = self.cleaned_data.get('phone_number', '')
        if phone_number:
            # Allow only digits, spaces, hyphens, and plus sign
            if not re.match(r'^[\d\s\-\+]+$', phone_number):
                raise forms.ValidationError('Phone number must contain only numbers, spaces, hyphens, and + sign.')
        return phone_number

    def clean_sections(self):
        import re
        sections = self.cleaned_data.get('sections', '')
        if not sections:
            return sections
        # Split by comma and validate each section
        section_list = [s.strip() for s in sections.split(',') if s.strip()]
        pattern = re.compile(r'^\d+-\d+$')  # Format: digit(s)-digit(s), e.g., 3-1, 4-2
        for section in section_list:
            if not pattern.match(section):
                raise forms.ValidationError(f'Invalid section format: "{section}". Sections must follow the format like "3-1", "4-2", etc.')
        return sections

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile.user = User.objects.get(pk=user.pk)
            profile.save()
            self.save_m2m()
        return profile

class CoordinatorProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    class Meta:
        model = CoordinatorProfile
        fields = [
            'first_name', 'last_name', 'email',
            'profile_image', 'phone_number', 'department', 'office',
        ]
        widgets = {
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_phone_number(self):
        """Validate that phone number contains only numbers, spaces, hyphens, and plus sign."""
        import re
        phone_number = self.cleaned_data.get('phone_number', '')
        if phone_number:
            # Allow only digits, spaces, hyphens, and plus sign
            if not re.match(r'^[\d\s\-\+]+$', phone_number):
                raise forms.ValidationError('Phone number must contain only numbers, spaces, hyphens, and + sign.')
        return phone_number
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile.user = User.objects.get(pk=user.pk)
            profile.save()
            self.save_m2m()
        return profile

class StudentInternshipProfileForm(forms.ModelForm):
    course = forms.ModelChoiceField(queryset=Course.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input skill-checkbox'}),
        required=False
    )
    class Meta:
        model = Internship
        fields = [
            'title', 'description', 'company', 'course', 'skills',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }
    class Media:
        js = ('js/internship_skills_autoload.js',)

class StudentDocumentUploadForm(forms.ModelForm):
    document_type = forms.ModelChoiceField(queryset=RequiredDocument.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))
    file = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    class Meta:
        model = StudentDocument
        fields = ['document_type', 'file']

class StudentCVUploadForm(forms.ModelForm):
    cv = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}), required=True)
    class Meta:
        model = StudentProfile
        fields = ['cv']

class AddSkillForm(forms.Form):
    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)
        if course:
            skill_queryset = Skill.objects.filter(course=course)
        else:
            skill_queryset = Skill.objects.all()
        self.fields['skill'] = forms.ModelChoiceField(
            queryset=skill_queryset,
            widget=forms.Select(attrs={'class': 'form-select'})
        )

class UpdateLocationForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['latitude', 'longitude', 'street', 'barangay', 'city', 'province']
        widgets = {
            'latitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'street': forms.TextInput(attrs={'class': 'form-control'}),
            'barangay': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['code', 'name', 'required_ojt_hours', 'description']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'required_ojt_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }

class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class StudentRegisterForm(UserCreationForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email.endswith('@cvsu.edu.ph'):
            raise forms.ValidationError('Please use your @cvsu.edu.ph email address.')
        return email
    
    def clean_first_name(self):
        """Validate that first name contains only letters and spaces."""
        first_name = self.cleaned_data.get('first_name', '')
        if first_name and not all(c.isalpha() or c.isspace() or c == '-' for c in first_name):
            raise forms.ValidationError('First name must contain only letters, spaces, and hyphens.')
        return first_name

    def clean_last_name(self):
        """Validate that last name contains only letters and spaces."""
        last_name = self.cleaned_data.get('last_name', '')
        if last_name and not all(c.isalpha() or c.isspace() or c == '-' for c in last_name):
            raise forms.ValidationError('Last name must contain only letters, spaces, and hyphens.')
        return last_name
    
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'username', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = User.UserType.STUDENT
        if commit:
            user.save()
        return user

class AdviserRegisterForm(UserCreationForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email.endswith('@cvsu.edu.ph'):
            raise forms.ValidationError('Please use your @cvsu.edu.ph email address.')
        return email
    
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '')
        if first_name and not all(c.isalpha() or c.isspace() or c == '-' for c in first_name):
            raise forms.ValidationError('First name must contain only letters, spaces, and hyphens.')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '')
        if last_name and not all(c.isalpha() or c.isspace() or c == '-' for c in last_name):
            raise forms.ValidationError('Last name must contain only letters, spaces, and hyphens.')
        return last_name
    
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'username', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = User.UserType.ADVISER
        if commit:
            user.save()
        return user

class CoordinatorRegisterForm(UserCreationForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email.endswith('@cvsu.edu.ph'):
            raise forms.ValidationError('Please use your @cvsu.edu.ph email address.')
        return email
    
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '')
        if first_name and not all(c.isalpha() or c.isspace() or c == '-' for c in first_name):
            raise forms.ValidationError('First name must contain only letters, spaces, and hyphens.')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '')
        if last_name and not all(c.isalpha() or c.isspace() or c == '-' for c in last_name):
            raise forms.ValidationError('Last name must contain only letters, spaces, and hyphens.')
        return last_name
    
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'username', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = User.UserType.COORDINATOR
        if commit:
            user.save()
        return user

class EmailVerificationCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 6-digit code'})
    )

class CoordinatorResignForm(forms.Form):
    new_coordinator_email = forms.EmailField(
        label='New Coordinator Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter @cvsu.edu.ph email'
        })
    )
    
    def clean_new_coordinator_email(self):
        email = self.cleaned_data.get('new_coordinator_email')
        if not email.endswith('@cvsu.edu.ph'):
            raise forms.ValidationError('Only @cvsu.edu.ph email addresses are allowed.')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered in the system.')
        return email
