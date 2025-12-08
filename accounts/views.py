from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from .models import User, StudentProfile, Skill, RequiredDocument, StudentDocument, AdviserProfile, Course, CoordinatorProfile, EmailVerificationCode
from .forms import StudentProfileForm, AdviserProfileForm, CoordinatorProfileForm, StudentDocumentUploadForm, StudentCVUploadForm, AddSkillForm, UpdateLocationForm, CourseChoices, CourseForm, SkillForm, StudentRegisterForm, AdviserRegisterForm, CoordinatorRegisterForm
from django.contrib.auth import login
from .models import DTR
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from datetime import datetime, timedelta
from .forms import EmailVerificationCodeForm
from .models import EmailVerificationCode

# Create your views here.
@login_required
@require_POST
def submit_dtr(request):
    user = request.user
    if not user.is_student:
        messages.error(request, 'Only students can submit DTRs.')
        return redirect('dashboard:home')
    profile = user.student_profile
    week_start = request.POST.get('week_start')
    week_end = request.POST.get('week_end')
    dtr_file = request.FILES.get('dtr_file')
    hours_rendered = request.POST.get('hours_rendered')
    adviser = profile.get_adviser() if hasattr(profile, 'get_adviser') else None
    if not adviser:
        messages.error(request, 'No adviser assigned. Cannot submit DTR.')
        return redirect('dashboard:home')
    try:
        dtr = DTR.objects.create(
            student=profile,
            adviser=adviser,
            week_start=week_start,
            week_end=week_end,
            file=dtr_file,
            hours_rendered=hours_rendered,
        )
        messages.success(request, 'DTR submitted successfully!')
    except Exception as e:
        messages.error(request, f'Error submitting DTR: {e}')
    return redirect(reverse('dashboard:home'))
# Profile views
@login_required
def profile_view(request):
    """View user profile based on user type."""
    user = request.user
    
    if user.is_student:
        try:
            # Always fetch the latest user object from the database
            user = User.objects.get(pk=user.pk)
            profile = user.student_profile
            # Build missing documents list
            uploaded_doc_ids = set(profile.documents.values_list('document_type_id', flat=True))
            required_documents = RequiredDocument.objects.all()
            missing_documents = [doc for doc in required_documents if doc.id not in uploaded_doc_ids]
            context = {
                'profile': profile,
                'documents': profile.documents.all(),
                'required_documents': required_documents,
                'missing_documents': missing_documents,
            }
            return render(request, 'accounts/student_profile.html', context)
        except StudentProfile.DoesNotExist:
            messages.warning(request, 'Please complete your profile.')
            return redirect('accounts:edit_profile')  # Changed from dashboard:home to accounts:edit_profile
    
    elif user.is_adviser:
        # Ensure adviser_profile exists and is linked
        try:
            profile = user.adviser_profile
        except (AttributeError, AdviserProfile.DoesNotExist):
            profile = AdviserProfile.objects.create(user=user, department="", sections="")
            user.user_type = User.UserType.ADVISER
            user.save()
            messages.info(request, 'Please complete your new adviser profile.')
            return redirect('accounts:edit_profile')
        # If profile is present, show adviser profile page or redirect to dashboard
        return redirect('dashboard:adviser_dashboard')
    
    elif user.is_coordinator:
        try:
            profile = user.coordinator_profile
            context = {
                'profile': profile,
            }
            return render(request, 'accounts/coordinator_profile.html', context)
        except:
            messages.warning(request, 'Your coordinator profile is not set up.')
            return redirect('accounts:edit_profile')  # Changed to edit profile
    
    # Default fallback
    return render(request, 'accounts/profile.html')

@login_required
def edit_profile(request):
    """Edit user profile for all user types."""
    user = request.user
    
    if user.is_student:
        try:
            profile = user.student_profile
        except StudentProfile.DoesNotExist:
            profile = StudentProfile(user=user)
            profile.save()
            messages.info(request, 'Please complete your new profile.')
        
        # Build course-skill map for JS
        from .models import Skill, Course
        course_skill_map = {}
        for course in Course.objects.all():
            skills = Skill.objects.filter(course=course).values('id', 'name')[:30]
            course_skill_map[course.id] = list(skills)
        
        if request.method == 'POST':
            form = StudentProfileForm(request.POST, request.FILES, instance=profile)
            import json
            skills_json = request.POST.get('skills_json', '[]')
            try:
                skills_data = json.loads(skills_json)
            except Exception:
                skills_data = []
            
            if form.is_valid():
                # First save the User model fields
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.email = form.cleaned_data['email']
                user.save()

                # Save the StudentProfile including student_id
                profile = form.save(commit=True)

                # Clear and set skills
                profile.skills.clear()
                for skill in skills_data:
                    if skill.get('custom'):
                        obj, _ = Skill.objects.get_or_create(name=skill['name'])
                        profile.skills.add(obj)
                    else:
                        try:
                            obj = Skill.objects.get(id=skill['id'])
                            profile.skills.add(obj)
                        except Skill.DoesNotExist:
                            pass

                # Refresh session user data
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, 'Profile updated successfully.')
                return redirect('accounts:profile')
        else:
            form = StudentProfileForm(instance=profile)
            # Always set initial values for user fields from the latest user model
            form.fields['first_name'].initial = user.first_name
            form.fields['last_name'].initial = user.last_name
            form.fields['email'].initial = user.email
        
        return render(request, 'accounts/edit_profile.html', {
            'form': form,
            'profile': profile,
            'course_skill_map': course_skill_map,
            'is_student': True,
            'is_adviser': False,
            'is_coordinator': False,
        })
    
    elif user.is_adviser:
        # Ensure adviser_profile exists and is linked
        try:
            profile = user.adviser_profile
        except (AttributeError, AdviserProfile.DoesNotExist):
            profile = AdviserProfile.objects.create(user=user, department="", sections="")
            user.user_type = User.UserType.ADVISER
            user.save()
            messages.info(request, 'Please complete your new adviser profile.')
        if request.method == 'POST':
            form = AdviserProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                # Save user fields explicitly
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.email = form.cleaned_data['email']
                user.save()
                profile = form.save(commit=False)
                profile.year_levels = form.cleaned_data.get('year_levels', '')
                profile.save()
                form.save_m2m()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, 'Profile updated successfully.')
                return redirect('dashboard:home')
        else:
            form = AdviserProfileForm(instance=profile)
            form.fields['first_name'].initial = user.first_name
            form.fields['last_name'].initial = user.last_name
            form.fields['email'].initial = user.email
        return render(request, 'accounts/edit_profile.html', {
            'form': form,
            'profile': profile,
            'is_student': False,
            'is_adviser': True,
            'is_coordinator': False,
        })
    
    elif user.is_coordinator:
        try:
            profile = user.coordinator_profile
        except AttributeError:  # Changed from bare except
            messages.warning(request, 'Your coordinator profile is not set up.')
            return redirect('dashboard:home')  # Or create profile flow
            
        if request.method == 'POST':
            form = CoordinatorProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('dashboard:home')
        else:
            form = CoordinatorProfileForm(instance=profile)
            form.fields['first_name'].initial = user.first_name
            form.fields['last_name'].initial = user.last_name
            form.fields['email'].initial = user.email
        return render(request, 'accounts/edit_profile.html', {
            'form': form,
            'profile': profile,
            'is_student': False,
            'is_adviser': False,
            'is_coordinator': True,
        })
    
    else:
        messages.warning(request, 'No profile type found.')
        return redirect('dashboard:home')

@login_required
def change_password(request):
    """Change user password."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

# Document management
@login_required
def document_list(request):
    """View list of student documents."""
    if not request.user.is_student:
        messages.error(request, 'Only students can access document management.')
        return redirect('dashboard:home')
    
    try:
        profile = request.user.student_profile
        context = {
            'documents': profile.documents.all(),
            'required_documents': RequiredDocument.objects.all(),
        }
        return render(request, 'accounts/document_list.html', context)
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')

@login_required
def upload_document(request):
    """Upload a student document."""
    if not request.user.is_student:
        messages.error(request, 'Only students can upload documents.')
        return redirect('dashboard:home')
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')
    if request.method == 'POST':
        form = StudentDocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.student = profile
            document.save()
            messages.success(request, 'Document uploaded successfully.')
            return redirect('accounts:document_list')
    else:
        form = StudentDocumentUploadForm()
    return render(request, 'accounts/upload_document.html', {'form': form})

@login_required
def delete_document(request, document_id):
    """Delete a student document."""
    if not request.user.is_student:
        messages.error(request, 'Only students can manage documents.')
        return redirect('dashboard:home')
    
    document = get_object_or_404(StudentDocument, id=document_id)
    
    # Check if the document belongs to the requesting user
    if document.student.user != request.user:
        messages.error(request, 'You do not have permission to delete this document.')
        return redirect('accounts:document_list')
    
    if request.method == 'POST':
        document.file.delete()  # Delete the actual file
        document.delete()       # Delete the database record
        messages.success(request, f'Document "{document.document_type.name}" deleted successfully.')
        return redirect('accounts:document_list')
    
    return render(request, 'accounts/confirm_delete_document.html', {'document': document})

# CV management
@login_required
def upload_cv(request):
    """Upload a CV."""
    if not request.user.is_student:
        messages.error(request, 'Only students can upload CV.')
        return redirect('dashboard:home')
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')
    if request.method == 'POST':
        form = StudentCVUploadForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'CV uploaded successfully.')
            return redirect('accounts:profile')
    else:
        form = StudentCVUploadForm(instance=profile)
    return render(request, 'accounts/upload_cv.html', {'form': form})

@login_required
def delete_cv(request):
    """Delete a CV."""
    if not request.user.is_student:
        messages.error(request, 'Only students can manage CV.')
        return redirect('dashboard:home')
    
    try:
        profile = request.user.student_profile
        if request.method == 'POST':
            if profile.cv:
                profile.cv.delete()  # Delete the actual file
                profile.cv = None
                profile.save()
                messages.success(request, 'CV deleted successfully.')
            else:
                messages.info(request, 'No CV to delete.')
            return redirect('accounts:profile')
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')
    
    return render(request, 'accounts/confirm_delete_cv.html')

# Skills management
@login_required
def manage_skills(request, course_id=None):
    from .models import Course as CourseModel, Skill as SkillModel
    if request.user.is_adviser:
        adviser = request.user.adviser_profile
        if course_id:
            course = get_object_or_404(Course, id=course_id, advisers=adviser)
            skills = Skill.objects.filter(course=course)
            course_id_for_suggestions = course.id
            course_name_for_suggestions = course.name
        else:
            course = None
            skills = Skill.objects.none()
            course_id_for_suggestions = None
            course_name_for_suggestions = ''
        # Build course_skill_map for JS
        course_skill_map = {}
        for c in CourseModel.objects.all():
            course_skill_map[c.id] = list(SkillModel.objects.filter(course=c).values('id', 'name'))
        return render(request, 'accounts/manage_skills.html', {
            'course': course,
            'skills': skills,
            'course_skill_map': course_skill_map,
            'selected_course_id': course_id_for_suggestions,
            'selected_course_name': course_name_for_suggestions
        })
    elif request.user.is_student:
        profile = request.user.student_profile
        if request.method == 'POST':
            import json
            skills_json = request.POST.get('skills_json', '[]')
            try:
                skills_data = json.loads(skills_json)
            except Exception:
                skills_data = []
            # Clear and set skills
            profile.skills.clear()
            from .models import Skill as SkillModel
            for skill in skills_data:
                if skill.get('custom'):
                    obj, _ = SkillModel.objects.get_or_create(name=skill['name'])
                    profile.skills.add(obj)
                else:
                    try:
                        obj = SkillModel.objects.get(id=skill['id'])
                        profile.skills.add(obj)
                    except SkillModel.DoesNotExist:
                        pass
            profile.save()
            messages.success(request, 'Skills updated successfully.')
            return redirect('accounts:profile')
        skills = profile.skills.all()
        # Build course_skill_map for JS
        course_skill_map = {}
        from .models import Course as CourseModel, Skill as SkillModel
        for c in CourseModel.objects.all():
            course_skill_map[c.id] = list(SkillModel.objects.filter(course=c).values('id', 'name'))
        selected_course_id = profile.course.id if profile.course else ''
        selected_course_name = profile.course.name if profile.course else ''
        return render(request, 'accounts/manage_skills.html', {
            'course': profile.course,
            'skills': skills,
            'course_skill_map': course_skill_map,
            'selected_course_id': selected_course_id,
            'selected_course_name': selected_course_name
        })
    else:
        messages.error(request, 'You do not have permission to manage skills.')
        return redirect('dashboard:home')

@login_required
def add_skill(request, course_id=None):
    if request.user.is_adviser:
        adviser = request.user.adviser_profile
        course = get_object_or_404(Course, id=course_id, advisers=adviser) if course_id else None
        if request.method == 'POST':
            form = SkillForm(request.POST)
            if form.is_valid():
                skill = form.save(commit=False)
                if course:
                    skill.course = course
                skill.save()
                messages.success(request, 'Skill added successfully.')
                if course:
                    return redirect('accounts:manage_skills', course_id=course.id)
                else:
                    return redirect('accounts:manage_skills')
        else:
            form = SkillForm()
        return render(request, 'accounts/skill_form.html', {'form': form, 'form_title': 'Add Skill', 'course': course})
    elif request.user.is_student:
        profile = request.user.student_profile
        if request.method == 'POST':
            form = SkillForm(request.POST)
            if form.is_valid():
                skill = form.save()
                profile.skills.add(skill)
                messages.success(request, 'Skill added to your profile.')
                return redirect('accounts:manage_skills')
        else:
            form = SkillForm()
        return render(request, 'accounts/skill_form.html', {'form': form, 'form_title': 'Add Skill', 'course': profile.course})
    else:
        messages.error(request, 'You do not have permission to add skills.')
        return redirect('dashboard:home')

@login_required
def edit_skill(request, course_id, skill_id):
    adviser = request.user.adviser_profile
    course = get_object_or_404(Course, id=course_id, advisers=adviser)
    skill = get_object_or_404(Skill, id=skill_id, course=course)
    if request.method == 'POST':
        form = SkillForm(request.POST, instance=skill)
        if form.is_valid():
            form.save()
            messages.success(request, 'Skill updated successfully.')
            return redirect('accounts:manage_skills', course_id=course.id)
    else:
        form = SkillForm(instance=skill)
    return render(request, 'accounts/skill_form.html', {'form': form, 'form_title': 'Edit Skill', 'course': course})

@login_required
def delete_skill(request, course_id, skill_id):
    adviser = request.user.adviser_profile
    course = get_object_or_404(Course, id=course_id, advisers=adviser)
    skill = get_object_or_404(Skill, id=skill_id, course=course)
    if request.method == 'POST':
        skill.delete()
        messages.success(request, 'Skill deleted successfully.')
        return redirect('accounts:manage_skills', course_id=course.id)
    return render(request, 'accounts/confirm_delete_skill.html', {'skill': skill, 'course': course})

# Location management
@login_required
def update_location(request):
    """Update student location using map."""
    if not request.user.is_student:
        messages.error(request, 'Only students can update location.')
        return redirect('dashboard:home')
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')
    if request.method == 'POST':
        form = UpdateLocationForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Location updated successfully.')
            return redirect('accounts:profile')
    else:
        form = UpdateLocationForm(instance=profile)
    return render(request, 'accounts/update_location.html', {'form': form})

@login_required
def user_list(request):
    """Coordinator: View all users (students, advisers, coordinators)."""
    if not request.user.is_coordinator:
        return render(request, '403.html')
    users = User.objects.all().order_by('user_type', 'last_name', 'first_name')
    return render(request, 'accounts/user_list.html', {'users': users})

# Adviser course management
@login_required
def manage_courses(request):
    """Adviser: Manage courses."""
    adviser = request.user.adviser_profile
    courses = adviser.courses.all()
    return render(request, 'accounts/manage_courses.html', {'courses': courses})

@login_required
def add_course(request):
    """Adviser: Add a new course."""
    adviser = request.user.adviser_profile
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            adviser.courses.add(course)
            messages.success(request, 'Course added successfully.')
            return redirect('accounts:manage_courses')
    else:
        form = CourseForm()
    return render(request, 'accounts/course_form.html', {'form': form, 'form_title': 'Add Course'})

@login_required
def edit_course(request, course_id):
    """Adviser: Edit an existing course."""
    adviser = request.user.adviser_profile
    course = get_object_or_404(Course, id=course_id, advisers=adviser)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully.')
            return redirect('accounts:manage_courses')
    else:
        form = CourseForm(instance=course)
    return render(request, 'accounts/course_form.html', {'form': form, 'form_title': 'Edit Course'})

@login_required
def delete_course(request, course_id):
    """Adviser: Delete a course."""
    adviser = request.user.adviser_profile
    course = get_object_or_404(Course, id=course_id, advisers=adviser)
    if request.method == 'POST':
        adviser.courses.remove(course)
        # Optionally, delete the course if no advisers are left
        if course.advisers.count() == 0:
            course.delete()
        messages.success(request, 'Course deleted successfully.')
        return redirect('accounts:manage_courses')
    return render(request, 'accounts/confirm_delete_course.html', {'course': course})

def student_register(request):
    """Student registration with session tracking for email verification."""
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Store user ID in session for email verification
            request.session['verifying_user_id'] = user.id
            request.session['verifying_user_email'] = user.email
            request.session['verification_session_time'] = datetime.now().isoformat()
            
            send_verification_code(user)
            messages.success(request, 'Registration successful! Please check your email for the 6-digit verification code.')
            return redirect('accounts:verify_email_code')
    else:
        form = StudentRegisterForm()
    return render(request, 'account/signup.html', {'form': form, 'register_type': 'student'})

def adviser_register(request):
    """Adviser registration with session tracking."""
    if request.method == 'POST':
        form = AdviserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            AdviserProfile.objects.create(user=user, department="", sections="")
            
            # Store user ID in session
            request.session['verifying_user_id'] = user.id
            request.session['verifying_user_email'] = user.email
            request.session['verification_session_time'] = datetime.now().isoformat()
            
            send_verification_code(user)
            messages.success(request, 'Adviser registration successful! Please check your email for the 6-digit verification code.')
            return redirect('accounts:verify_email_code')
    else:
        form = AdviserRegisterForm()
    return render(request, 'account/signup.html', {'form': form, 'register_type': 'adviser'})

def coordinator_register(request):
    """Coordinator registration with session tracking."""
    if request.method == 'POST':
        form = CoordinatorRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            CoordinatorProfile.objects.create(user=user, department="")
            
            # Store user ID in session
            request.session['verifying_user_id'] = user.id
            request.session['verifying_user_email'] = user.email
            request.session['verification_session_time'] = datetime.now().isoformat()
            
            send_verification_code(user)
            messages.success(request, 'Coordinator registration successful! Please check your email for the 6-digit verification code.')
            return redirect('accounts:verify_email_code')
    else:
        form = CoordinatorRegisterForm()
    return render(request, 'account/signup.html', {'form': form, 'register_type': 'coordinator'})

@login_required
def update_ojt_status(request):
    if not request.user.is_student:
        messages.error(request, 'Only students can update OJT status.')
        return redirect('accounts:profile')
    profile = request.user.student_profile
    if request.method == 'POST':
        new_status = request.POST.get('ojt_status')
        if new_status in dict(profile.OJTStatus.choices):
            profile.ojt_status = new_status
            profile.save()
            messages.success(request, 'OJT status updated!')
        else:
            messages.error(request, 'Invalid OJT status.')
    return redirect('accounts:profile')

@login_required
def remove_skill(request, skill_id):
    if request.user.is_student:
        profile = request.user.student_profile
        skill = get_object_or_404(Skill, id=skill_id)
        profile.skills.remove(skill)
        messages.success(request, 'Skill removed successfully.')
        return redirect('accounts:manage_skills')
    elif request.user.is_adviser:
        # Optionally, allow advisers to remove skills from their course
        messages.error(request, 'Advisers cannot remove skills here.')
        return redirect('accounts:manage_skills')
    else:
        messages.error(request, 'You do not have permission to remove skills.')
        return redirect('dashboard:home')

def send_verification_code(user):
    """
    Send email verification code to user.
    Returns True if successful, False otherwise.
    """
    try:
        # Invalidate previous codes
        EmailVerificationCode.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Generate new code
        code = EmailVerificationCode.generate_code()
        EmailVerificationCode.objects.create(user=user, code=code)
        
        # Get email settings
        from django.conf import settings
        
        # Send email
        send_mail(
            'Verify Your Email - CVSU Internship Matching',
            f'Hello {user.get_full_name() or user.username},\n\n'
            f'Your email verification code is: {code}\n\n'
            f'This code will expire in 15 minutes.\n\n'
            f'Thank you,\nCVSU Internship Matching Team',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
        
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send verification email: {e}")
        return False

def verify_email_code(request):
    """
    Verify email verification code from session-stored user.
    """
    error = None
    
    # Get user info from session
    user_id = request.session.get('verifying_user_id')
    user_email = request.session.get('verifying_user_email')
    session_time_str = request.session.get('verification_session_time')
    
    # Check if session exists
    if not user_id:
        messages.error(request, 'No verification session found. Please register again.')
        return redirect('accounts:register_choice')
    
    # Check if session is expired (30 minutes)
    if session_time_str:
        try:
            session_time = datetime.fromisoformat(session_time_str)
            if datetime.now() - session_time > timedelta(minutes=30):
                # Clear expired session
                request.session.flush()
                messages.error(request, 'Verification session expired. Please register again.')
                return redirect('accounts:register_choice')
        except ValueError:
            pass  # If date parsing fails, continue anyway
    
    if request.method == 'POST':
        form = EmailVerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            try:
                # Get user from session ID
                user = User.objects.get(id=user_id)
                
                # Find matching, unused code
                code_obj = EmailVerificationCode.objects.filter(
                    user=user, 
                    code=code, 
                    is_used=False
                ).order_by('-created_at').first()
                
                if code_obj:
                    # Check if code is expired (15 minutes)
                    code_age = datetime.now() - code_obj.created_at.replace(tzinfo=None)
                    if code_age > timedelta(minutes=15):
                        error = 'Verification code has expired. Please request a new one.'
                    else:
                        # Mark code as used
                        code_obj.is_used = True
                        code_obj.save()
                        
                        # Activate user account
                        user.is_active = True
                        user.save()
                        
                        # Log the user in
                        login(request, user)
                        
                        # Clear verification session
                        if 'verifying_user_id' in request.session:
                            del request.session['verifying_user_id']
                        if 'verifying_user_email' in request.session:
                            del request.session['verifying_user_email']
                        if 'verification_session_time' in request.session:
                            del request.session['verification_session_time']
                        
                        messages.success(request, 'Email verified successfully! You are now logged in.')
                        return redirect('dashboard:home')
                else:
                    error = 'Invalid or expired verification code.'
                    
            except User.DoesNotExist:
                error = 'User not found. Please register again.'
                # Clear invalid session
                request.session.flush()
                
    else:
        form = EmailVerificationCodeForm()
    
    # Render verification page with user email
    context = {
        'form': form,
        'error': error,
        'user_email': user_email,  # Show user which email the code was sent to
    }
    return render(request, 'accounts/verify_code.html', context)

def resend_verification(request):
    """
    Resend verification code to session user.
    """
    user_id = request.session.get('verifying_user_id')
    user_email = request.session.get('verifying_user_email')
    
    if not user_id:
        messages.error(request, 'No verification session found. Please register again.')
        return redirect('accounts:register_choice')
    
    try:
        user = User.objects.get(id=user_id)
        if send_verification_code(user):
            messages.success(request, f'Verification code resent to {user_email}!')
        else:
            messages.error(request, 'Failed to resend verification code. Please try again.')
    except User.DoesNotExist:
        messages.error(request, 'User not found. Please register again.')
        return redirect('accounts:register_choice')
    
    return redirect('accounts:verify_email_code')

def register_choice(request):
    """
    Page to choose registration type.
    """
    return render(request, 'accounts/register_choice.html')