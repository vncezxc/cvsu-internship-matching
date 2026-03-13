from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.conf import settings
from .models import User, StudentProfile, Skill, RequiredDocument, StudentDocument, AdviserProfile, Course, CoordinatorProfile, EmailVerificationCode, DeactivationRequest, AdviserMasterListEntry
from .forms import StudentProfileForm, AdviserProfileForm, CoordinatorProfileForm, StudentDocumentUploadForm, StudentCVUploadForm, AddSkillForm, UpdateLocationForm, CourseChoices, CourseForm, SkillForm, StudentRegisterForm, AdviserRegisterForm, CoordinatorRegisterForm
from django.contrib.auth import login
from .models import DTR
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from datetime import datetime, timedelta
from .forms import EmailVerificationCodeForm
from .models import EmailVerificationCode
from django.utils import timezone
import pytz
from allauth.account.models import EmailAddress

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
                def normalize_name(value):
                    return ' '.join(str(value or '').strip().lower().split())

                student_id = (form.cleaned_data.get('student_id') or '').strip()
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                full_name = normalize_name(f"{first_name} {last_name}")
                course = form.cleaned_data.get('course')
                section = (form.cleaned_data.get('section') or '').strip()

                if not student_id or not full_name or not course or not section:
                    messages.error(request, 'Please complete Student ID, full name, course, and section before saving.')
                    return render(request, 'accounts/edit_profile.html', {
                        'form': form,
                        'profile': profile,
                        'course_skill_map': course_skill_map,
                        'is_student': True,
                        'is_adviser': False,
                        'is_coordinator': False,
                    })

                advisers = AdviserProfile.objects.filter(courses=course)
                matching_advisers = [a for a in advisers if section in a.get_sections_list()]

                if not matching_advisers:
                    messages.error(request, 'No adviser master list found for your course and section. Please contact your adviser.')
                    return render(request, 'accounts/edit_profile.html', {
                        'form': form,
                        'profile': profile,
                        'course_skill_map': course_skill_map,
                        'is_student': True,
                        'is_adviser': False,
                        'is_coordinator': False,
                    })

                entries = AdviserMasterListEntry.objects.filter(adviser__in=matching_advisers, student_id=student_id)
                matched = any(normalize_name(entry.full_name) == full_name for entry in entries)

                if not matched:
                    messages.error(request, 'Your information does not match the adviser master list. Please contact your adviser.')
                    return render(request, 'accounts/edit_profile.html', {
                        'form': form,
                        'profile': profile,
                        'course_skill_map': course_skill_map,
                        'is_student': True,
                        'is_adviser': False,
                        'is_coordinator': False,
                    })

                # First save the User model fields
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.email = form.cleaned_data['email']
                user.save()

                # Save the StudentProfile including student_id
                profile = form.save(commit=True)
                profile.master_list_verified = True
                profile.save(update_fields=['master_list_verified'])

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
                from django.contrib.auth import update_session_auth_hash, logout
                update_session_auth_hash(request, user)
                
                # If adviser is not approved, log them out and redirect to login
                if not user.is_approved:
                    # Deactivate user until coordinator approves
                    user.is_active = False
                    user.save()
                    logout(request)
                    messages.success(request, 'Profile completed successfully! Your adviser account is now pending coordinator approval. You will receive an email once approved.')
                    return redirect('account_login')
                else:
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

@login_required
def pending_adviser_approvals(request):
    """Coordinator: View all pending adviser registrations."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only coordinators can approve advisers.')
        return redirect('dashboard:home')
    
    pending_advisers = User.objects.filter(
        user_type=User.UserType.ADVISER,
        is_approved=False
    ).order_by('-date_joined')
    
    return render(request, 'accounts/pending_adviser_approvals.html', {
        'pending_advisers': pending_advisers
    })

@login_required
def approve_adviser(request, user_id):
    """Coordinator: Approve an adviser registration."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only coordinators can approve advisers.')
        return redirect('dashboard:home')
    
    adviser = get_object_or_404(User, id=user_id, user_type=User.UserType.ADVISER)
    adviser.is_approved = True
    adviser.is_active = True
    adviser.save()
    
    # Send approval email
    send_mail(
        'Adviser Account Approved - CVSU Internship Matching',
        f'Hello {adviser.get_full_name()},\n\n'
        f'Your adviser account has been approved by the OJT Coordinator.\n'
        f'You can now log in and complete your profile.\n\n'
        f'Thank you,\nCVSU Internship Matching Team',
        settings.DEFAULT_FROM_EMAIL,
        [adviser.email],
        fail_silently=False,
    )
    
    messages.success(request, f'Adviser {adviser.get_full_name()} has been approved.')
    return redirect('accounts:pending_adviser_approvals')

@login_required
def reject_adviser(request, user_id):
    """Coordinator: Reject an adviser registration."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only coordinators can reject advisers.')
        return redirect('dashboard:home')
    
    adviser = get_object_or_404(User, id=user_id, user_type=User.UserType.ADVISER)
    
    # Send rejection email
    send_mail(
        'Adviser Account Not Approved - CVSU Internship Matching',
        f'Hello {adviser.get_full_name()},\n\n'
        f'Unfortunately, your adviser account registration was not approved.\n'
        f'Please contact the OJT Coordinator for more information.\n\n'
        f'Thank you,\nCVSU Internship Matching Team',
        settings.DEFAULT_FROM_EMAIL,
        [adviser.email],
        fail_silently=False,
    )
    
    # Delete the user
    adviser.delete()
    
    messages.success(request, f'Adviser {adviser.get_full_name()} has been rejected and removed.')
    return redirect('accounts:pending_adviser_approvals')

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
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Start as inactive
            user.save()
            
            # Create EmailAddress record for AllAuth
            EmailAddress.objects.create(
                user=user,
                email=user.email,
                verified=False,  # Start as unverified
                primary=True
            )
            
            request.session['verifying_user_id'] = user.id
            request.session['verifying_user_email'] = user.email
            request.session['verification_session_time'] = timezone.now().isoformat()
            
            send_verification_code(user)
            messages.success(request, 'Registration successful! Please check your email for verification.')
            return redirect('accounts:verify_email_code')
    else:
        form = StudentRegisterForm()
    coordinator_exists = User.objects.filter(user_type=User.UserType.COORDINATOR).exists()
    return render(request, 'account/signup.html', {'form': form, 'register_type': 'student', 'coordinator_exists': coordinator_exists})

# adviser_register
def adviser_register(request):
    if request.method == 'POST':
        form = AdviserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Start as inactive
            user.is_approved = False  # Requires coordinator approval
            user.save()
            AdviserProfile.objects.create(user=user, department="", sections="")
            
            # Create EmailAddress record for AllAuth
            EmailAddress.objects.create(
                user=user,
                email=user.email,
                verified=False,
                primary=True
            )
            
            request.session['verifying_user_id'] = user.id
            request.session['verifying_user_email'] = user.email
            request.session['verification_session_time'] = timezone.now().isoformat()
            
            send_verification_code(user)
            messages.success(request, 'Adviser registration successful! Please check your email for verification. Your account will be activated after coordinator approval.')
            return redirect('accounts:verify_email_code')
    else:
        form = AdviserRegisterForm()
    coordinator_exists = User.objects.filter(user_type=User.UserType.COORDINATOR).exists()
    return render(request, 'account/signup.html', {'form': form, 'register_type': 'adviser', 'coordinator_exists': coordinator_exists})

# coordinator_register
def coordinator_register(request):
    # Check if a coordinator already exists
    if User.objects.filter(user_type=User.UserType.COORDINATOR).exists():
        messages.error(request, 'A coordinator already exists in the system. Only one coordinator is allowed.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = CoordinatorRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Start as inactive
            user.save()
            CoordinatorProfile.objects.create(user=user, department="")
            
            # Create EmailAddress record for AllAuth
            EmailAddress.objects.create(
                user=user,
                email=user.email,
                verified=False,
                primary=True
            )
            
            request.session['verifying_user_id'] = user.id
            request.session['verifying_user_email'] = user.email
            request.session['verification_session_time'] = timezone.now().isoformat()
            
            send_verification_code(user)
            messages.success(request, 'Coordinator registration successful! Please check your email for verification.')
            return redirect('accounts:verify_email_code')
    else:
        form = CoordinatorRegisterForm()
    coordinator_exists = User.objects.filter(user_type=User.UserType.COORDINATOR).exists()
    return render(request, 'account/signup.html', {'form': form, 'register_type': 'coordinator', 'coordinator_exists': coordinator_exists})

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
    Send email verification code to user ONLY if not already active/verified.
    """
    # Check if user is already active AND email is verified in AllAuth
    from allauth.account.models import EmailAddress
    
    try:
        email_address = EmailAddress.objects.get(email=user.email, user=user)
        if email_address.verified and user.is_active:
            print(f"[DEBUG] User {user.email} is already verified in both systems.")
            return True
    except EmailAddress.DoesNotExist:
        pass
    
    # If user is active but AllAuth doesn't know, still send?
    if user.is_active:
        print(f"[DEBUG] User {user.email} is active but AllAuth not synced. Sending code anyway.")
    
    try:
        # Clean up old codes
        from django.utils import timezone
        from datetime import timedelta
        thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
        EmailVerificationCode.objects.filter(
            user=user, 
            created_at__lt=thirty_minutes_ago
        ).delete()
        
        # Invalidate any unused codes
        EmailVerificationCode.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Generate new code
        code = EmailVerificationCode.generate_code()
        EmailVerificationCode.objects.create(user=user, code=code)
        
        from django.conf import settings
        
        send_mail(
            'Verify Your Email - CVSU Internship Matching',
            f'Hello {user.get_full_name() or user.username},\n\n'
            f'Your email verification code is: {code}\n\n'
            f'This code will expire in 30 minutes.\n\n'
            f'Thank you,\nCVSU Internship Matching Team',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        print(f"[EMAIL] Verification code sent to {user.email}")
        return True
        
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send verification email: {e}")
        return False

def verify_email_code(request):
    """
    Verify email verification code and sync with AllAuth.
    """
    # If already logged in and verified, redirect home
    if request.user.is_authenticated and request.user.is_active:
        # Double-check AllAuth sync
        try:
            email_address = EmailAddress.objects.get(email=request.user.email, user=request.user)
            if not email_address.verified:
                email_address.verified = True
                email_address.save()
                print(f"[SYNC] Synced AllAuth for logged-in user {request.user.email}")
        except EmailAddress.DoesNotExist:
            pass
        return redirect('dashboard:home')
    
    user_id = request.session.get('verifying_user_id')
    user_email = request.session.get('verifying_user_email')
    session_time_str = request.session.get('verification_session_time')
    
    # Check session expiry (60 minutes)
    if session_time_str:
        try:
            session_time = datetime.fromisoformat(session_time_str)
            if timezone.now() - session_time > timedelta(minutes=60):
                request.session.flush()
                messages.error(request, 'Session expired. Please register again.')
                return redirect('accounts:register_choice')
        except ValueError:
            pass
    
    if not user_id:
        messages.error(request, 'No verification session found. Please login or register.')
        return redirect('account_login')
    
    if request.method == 'POST':
        form = EmailVerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            try:
                user = User.objects.get(id=user_id)
                
                # Check if already verified in BOTH systems
                try:
                    email_address = EmailAddress.objects.get(email=user.email, user=user)
                    if email_address.verified and user.is_active:
                        # Already fully verified, just log in
                        user.backend = 'django.contrib.auth.backends.ModelBackend'
                        login(request, user)
                        messages.info(request, 'Account already verified. Logged in.')
                        return redirect('dashboard:home')
                except EmailAddress.DoesNotExist:
                    pass
                
                # Check verification code
                code_obj = EmailVerificationCode.objects.filter(
                    user=user, code=code, is_used=False
                ).first()
                
                if code_obj:
                    # Check code expiry (30 minutes)
                    if timezone.now() - code_obj.created_at > timedelta(minutes=30):
                        messages.error(request, 'Verification code has expired.')
                        code_obj.delete()
                    else:
                        # Mark code as used
                        code_obj.is_used = True
                        code_obj.save()
                        
                        # 1. ACTIVATE USER in Django
                        # For advisers: temporarily activate to allow profile completion
                        user.is_active = True
                        user.save()
                        
                        # 2. VERIFY in AllAuth EmailAddress
                        try:
                            email_address = EmailAddress.objects.get(
                                email=user.email, 
                                user=user
                            )
                            email_address.verified = True
                            email_address.primary = True
                            email_address.save()
                            print(f"[SYNC] Verified in AllAuth: {user.email}")
                        except EmailAddress.DoesNotExist:
                            # Create if doesn't exist
                            EmailAddress.objects.create(
                                user=user,
                                email=user.email,
                                verified=True,
                                primary=True
                            )
                            print(f"[SYNC] Created and verified in AllAuth: {user.email}")
                        
                        # 3. Login user
                        user.backend = 'django.contrib.auth.backends.ModelBackend'
                        login(request, user)
                        
                        # 4. Clear session
                        request.session.pop('verifying_user_id', None)
                        request.session.pop('verifying_user_email', None)
                        request.session.pop('verification_session_time', None)
                        
                        # 5. Redirect advisers to edit profile, others to dashboard
                        if user.is_adviser and not user.is_approved:
                            messages.success(request, 'Email verified successfully! Please complete your profile. Your account will be reviewed by the coordinator after you submit your profile.')
                            return redirect('accounts:edit_profile')
                        else:
                            messages.success(request, 'Email verified successfully! You are now logged in.')
                            return redirect('dashboard:home')
                else:
                    messages.error(request, 'Invalid or expired verification code.')
                    
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
                request.session.flush()
                
    else:
        form = EmailVerificationCodeForm()
    
    return render(request, 'accounts/verify_code.html', {
        'form': form,
        'user_email': user_email,
    })

def resend_verification(request):
    """
    Resend verification code.
    """
    user_id = request.session.get('verifying_user_id')
    user_email = request.session.get('verifying_user_email')
    
    if not user_id:
        messages.error(request, 'No verification session found.')
        return redirect('accounts:register_choice')
    
    try:
        user = User.objects.get(id=user_id)
        
        # Check if already verified
        from allauth.account.models import EmailAddress
        try:
            email_address = EmailAddress.objects.get(email=user.email, user=user)
            if email_address.verified and user.is_active:
                messages.info(request, 'Your email is already verified.')
                return redirect('accounts:verify_email_code')
        except EmailAddress.DoesNotExist:
            pass
        
        # Resend code
        if send_verification_code(user):
            messages.success(request, f'New verification code sent to {user_email}')
        else:
            messages.error(request, 'Failed to resend verification code.')
            
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        request.session.flush()
    
    return redirect('accounts:verify_email_code')

def register_choice(request):
    """
    Page to choose registration type.
    """
    return render(request, 'accounts/register_choice.html')

def debug_codes(request):
    """Debug endpoint to check verification codes"""
    user_id = request.session.get('verifying_user_id')
    
    if not user_id:
        return JsonResponse({'error': 'No user in session'})
    
    try:
        user = User.objects.get(id=user_id)
        codes = EmailVerificationCode.objects.filter(user=user).order_by('-created_at')
        
        codes_list = []
        for code in codes:
            codes_list.append({
                'code': code.code,
                'created_at': str(code.created_at),
                'is_used': code.is_used,
                'age_minutes': (timezone.now() - code.created_at).total_seconds() / 60,
            })
        
        return JsonResponse({
            'user': user.email,
            'current_time': str(timezone.now()),
            'codes': codes_list,
            'session_user_id': user_id,
        })
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'})

@login_required
def coordinator_resign(request):
    """Coordinator can resign and invite a new coordinator"""
    if not request.user.is_coordinator:
        messages.error(request, 'Only coordinators can access this page.')
        return redirect('dashboard:home')
    
    from .forms import CoordinatorResignForm
    from .models import CoordinatorInvitation
    from datetime import timedelta
    
    if request.method == 'POST':
        form = CoordinatorResignForm(request.POST)
        if form.is_valid():
            new_email = form.cleaned_data['new_coordinator_email']
            
            # Create invitation token (expires in 7 days)
            invitation = CoordinatorInvitation.objects.create(
                email=new_email,
                invited_by=request.user,
                expires_at=timezone.now() + timedelta(days=7)
            )
            
            # Send invitation email
            registration_url = request.build_absolute_uri(
                f'/accounts/register/coordinator/{invitation.token}/'
            )
            
            send_mail(
                subject='CVSU Internship System - Coordinator Invitation',
                message=f'''Hello,

You have been invited to become the new OJT Coordinator for the CVSU Bacoor Internship Matching System.

The current coordinator, {request.user.get_full_name()}, is transferring the role to you.

Please click the link below to register as the new coordinator:
{registration_url}

This link will expire in 7 days.

If you did not expect this invitation, please ignore this email.

Best regards,
CVSU Bacoor Internship System
''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[new_email],
                fail_silently=False,
            )
            
            messages.success(request, f'Invitation sent to {new_email}. Once they register, your coordinator role will be transferred.')
            return redirect('dashboard:coordinator_dashboard')
    else:
        form = CoordinatorResignForm()
    
    return render(request, 'accounts/coordinator_resign.html', {'form': form})

def coordinator_register_with_token(request, token):
    """Special registration for invited coordinators"""
    from .models import CoordinatorInvitation
    
    try:
        invitation = CoordinatorInvitation.objects.get(token=token)
    except CoordinatorInvitation.DoesNotExist:
        messages.error(request, 'Invalid invitation link.')
        return redirect('accounts:login')
    
    if not invitation.is_valid():
        messages.error(request, 'This invitation has expired or been used.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        from .forms import CoordinatorRegisterForm
        form = CoordinatorRegisterForm(request.POST)
        
        # Validate that email matches invitation
        if form.is_valid():
            if form.cleaned_data['email'] != invitation.email:
                messages.error(request, 'Email must match the invited email address.')
            else:
                user = form.save(commit=False)
                user.is_active = False
                user.save()
                CoordinatorProfile.objects.create(user=user, department="")
                
                # Create EmailAddress for AllAuth
                EmailAddress.objects.create(
                    user=user,
                    email=user.email,
                    verified=False,
                    primary=True
                )
                
                # Mark invitation as used
                invitation.is_used = True
                invitation.save()
                
                # Deactivate old coordinator
                old_coordinator = invitation.invited_by
                old_coordinator.user_type = User.UserType.ADVISER  # Demote to adviser
                old_coordinator.is_active = False
                old_coordinator.save()
                
                request.session['verifying_user_id'] = user.id
                request.session['verifying_user_email'] = user.email
                request.session['verification_session_time'] = timezone.now().isoformat()
                
                send_verification_code(user)
                messages.success(request, 'Registration successful! Please verify your email. The previous coordinator has been deactivated.')
                return redirect('accounts:verify_email_code')
    else:
        from .forms import CoordinatorRegisterForm
        form = CoordinatorRegisterForm(initial={'email': invitation.email})
    
    return render(request, 'account/signup.html', {
        'form': form,
        'register_type': 'coordinator',
        'invitation_token': token,
        'invited_email': invitation.email
    })

# Student Account Deactivation Views
@login_required
def request_deactivation(request):
    """Student requests account deactivation."""
    if not request.user.is_student:
        messages.error(request, 'Only students can request account deactivation.')
        return redirect('dashboard:home')
    
    profile = request.user.student_profile
    
    # Check if OJT status is COMPLETED
    if profile.ojt_status != StudentProfile.OJTStatus.COMPLETED:
        messages.error(request, 'You can only request deactivation after completing your OJT.')
        return redirect('accounts:profile')
    
    # Check if there's already a pending request
    existing_request = DeactivationRequest.objects.filter(
        student=request.user,
        status=DeactivationRequest.Status.PENDING
    ).first()
    
    if existing_request:
        messages.warning(request, 'You already have a pending deactivation request.')
        return redirect('accounts:profile')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        DeactivationRequest.objects.create(
            student=request.user,
            reason=reason
        )
        messages.success(request, 'Deactivation request submitted. The coordinator will review it.')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/request_deactivation.html')


@login_required
def coordinator_deactivation_requests(request):
    """Coordinator views pending deactivation requests."""
    if request.user.user_type != User.UserType.COORDINATOR:
        messages.error(request, 'Only coordinators can view deactivation requests.')
        return redirect('dashboard:home')
    
    pending_requests = DeactivationRequest.objects.filter(status=DeactivationRequest.Status.PENDING)
    processed_requests = DeactivationRequest.objects.filter(status__in=[DeactivationRequest.Status.APPROVED, DeactivationRequest.Status.REJECTED])[:20]
    
    context = {
        'pending_requests': pending_requests,
        'processed_requests': processed_requests,
    }
    return render(request, 'accounts/coordinator_deactivation_requests.html', context)


@login_required
@require_POST
def approve_deactivation(request, request_id):
    """Coordinator approves a deactivation request."""
    if request.user.user_type != User.UserType.COORDINATOR:
        messages.error(request, 'Only coordinators can approve deactivation requests.')
        return redirect('dashboard:home')
    
    deactivation_request = get_object_or_404(DeactivationRequest, id=request_id, status=DeactivationRequest.Status.PENDING)
    
    # Deactivate the student account
    student_user = deactivation_request.student
    student_user.is_active = False
    student_user.save()
    
    # Update the request
    deactivation_request.status = DeactivationRequest.Status.APPROVED
    deactivation_request.processed_by = request.user
    deactivation_request.processed_at = timezone.now()
    deactivation_request.save()
    
    messages.success(request, f'Account for {student_user.get_full_name()} has been deactivated.')
    return redirect('accounts:coordinator_deactivation_requests')


@login_required
@require_POST
def reject_deactivation(request, request_id):
    """Coordinator rejects a deactivation request."""
    if request.user.user_type != User.UserType.COORDINATOR:
        messages.error(request, 'Only coordinators can reject deactivation requests.')
        return redirect('dashboard:home')
    
    deactivation_request = get_object_or_404(DeactivationRequest, id=request_id, status=DeactivationRequest.Status.PENDING)
    
    rejection_reason = request.POST.get('rejection_reason', '')
    
    # Update the request
    deactivation_request.status = DeactivationRequest.Status.REJECTED
    deactivation_request.processed_by = request.user
    deactivation_request.processed_at = timezone.now()
    deactivation_request.rejection_reason = rejection_reason
    deactivation_request.save()
    
    messages.success(request, f'Deactivation request for {deactivation_request.student.get_full_name()} has been rejected.')
    return redirect('accounts:coordinator_deactivation_requests')        