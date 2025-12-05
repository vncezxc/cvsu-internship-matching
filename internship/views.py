from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Company, Internship, Application, CompanyReview
from accounts.models import StudentProfile, Skill, Course
from .forms import InternshipForm
from .forms import CompanyForm, CompanyReviewForm, ApplicationStatusUpdateForm
from django.db import models

# Create your views here.

@login_required
@require_POST
def delete_internship(request, internship_id):
    internship = get_object_or_404(Internship, id=internship_id)
    internship.delete()
    messages.success(request, 'Internship deleted successfully.')
    return redirect('internship:internships')
# Student views
@login_required
def internship_matches(request):
    """View internship matches for a student."""
    if not request.user.is_student:
        messages.error(request, 'Only students can access internship matches.')
        return redirect('dashboard:home')
    
    try:
        profile = request.user.student_profile
        
        # Check if profile is complete for matching (course, skills, pinned location)
        if not profile.profile_is_complete_for_matching:
            messages.warning(request, 'Please complete your profile before applying.')
            return redirect('accounts:edit_profile')
        
        # Get all active internships
        internships = Internship.objects.filter(is_active=True)

        # Filter by course if specified (recommended_courses is a M2M field)
        if profile.course:
            internships = internships.filter(recommended_courses=profile.course)

        # Calculate match scores for each internship
        matches = []
        for internship in internships:
            # Skip internships the student has already applied to
            if Application.objects.filter(student=profile, internship=internship).exists():
                continue


            # Skill match: percent of required_skills that student has
            required_skills = set(internship.required_skills.values_list('id', flat=True))
            student_skills = set(profile.skills.values_list('id', flat=True))
            if required_skills:
                skill_match = len(required_skills & student_skills) / len(required_skills)
            else:
                skill_match = 1.0

            # Course match: 1.0 if course matches, else 0.0
            course_match = 1.0 if profile.course in internship.recommended_courses.all() else 0.0

            # Map/location match: if both have lat/lng, use distance (within 10km = 1.0, 10-30km = 0.5, else 0)
            def haversine(lat1, lon1, lat2, lon2):
                from math import radians, sin, cos, sqrt, atan2
                R = 6371  # Earth radius in km
                dlat = radians(lat2 - lat1)
                dlon = radians(lon2 - lon1)
                a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                return R * c

            company = internship.company
            map_match = 0.0
            if (company.latitude and company.longitude and profile.latitude and profile.longitude):
                try:
                    dist = haversine(float(company.latitude), float(company.longitude), float(profile.latitude), float(profile.longitude))
                    if dist <= 10:
                        map_match = 1.0
                    elif dist <= 30:
                        map_match = 0.5
                except Exception:
                    map_match = 0.0

            # Softer matching: 40% skills, 30% course, 30% map
            match_score = round(skill_match * 40 + course_match * 30 + map_match * 30)

            # Provide breakdown percentages for template display
            skill_pct = int(round(skill_match * 100))
            course_pct = int(round(course_match * 100))
            map_pct = int(round(map_match * 100))

            if match_score > 0:
                matches.append({
                    'internship': internship,
                    'score': match_score,
                    'distance_km': round(dist, 1) if map_match > 0 else None,
                    'skill_pct': skill_pct,
                    'course_pct': course_pct,
                    'map_pct': map_pct,
                })

        # Sort by match score (highest first)
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        # Pagination
        paginator = Paginator(matches, 10)  # Show 10 matches per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'matches': page_obj,
            'profile': profile,
        }
        return render(request, 'internship/matches.html', context)
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')

@login_required
def application_history(request):
    """View application history for a student."""
    if not request.user.is_student:
        messages.error(request, 'Only students can access application history.')
        return redirect('dashboard:home')
    
    try:
        profile = request.user.student_profile
        applications = Application.objects.filter(student=profile).order_by('-applied_at')
        
        # Pagination
        paginator = Paginator(applications, 10)  # Show 10 applications per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'applications': page_obj,
            'profile': profile,
        }
        return render(request, 'internship/application_history.html', context)
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')

@login_required
def apply_internship(request, internship_id):
    """Apply for an internship."""
    if not request.user.is_student:
        messages.error(request, 'Only students can apply for internships.')
        return redirect('dashboard:home')
    
    internship = get_object_or_404(Internship, id=internship_id, is_active=True)
    
    try:
        profile = request.user.student_profile
        
        # Check if already applied
        if Application.objects.filter(student=profile, internship=internship).exists():
            messages.warning(request, f'You have already applied to {internship.title} at {internship.company.name}.')
            return redirect('internship:applications')
        
        # Check if profile is complete
        if not profile.profile_is_complete_for_matching:
            messages.warning(request, 'Please complete your profile before applying.')
            return redirect('accounts:edit_profile')
        
        # Check if CV is uploaded
        if not profile.cv:
            messages.warning(request, 'Please upload your CV before applying.')
            return redirect('accounts:upload_cv')
        
        if request.method == 'POST':
            # Calculate match score
            match_score = internship.get_match_score(profile)
            
            # Create application
            application = Application.objects.create(
                student=profile,
                internship=internship,
                match_score=match_score
            )
            
            # Send a professional, detailed application email to the company
            from django.core.mail import EmailMessage
            student_user = request.user
            student_profile = profile
            subject = f"Internship Application: {internship.title} - {student_profile.get_full_name()}"
            skills = ', '.join([s.name for s in student_profile.skills.all()]) or 'N/A'
            address = student_profile.get_full_address()
            cv_url = student_profile.cv.url if student_profile.cv else 'No CV uploaded.'
            message = f"""
Dear {internship.company.name} HR Team,

I hope this message finds you well.

My name is {student_profile.get_full_name()} and I am a {student_profile.get_year_level_display()} student of {student_profile.course} at Cavite State University. I am writing to formally apply for the internship position "{internship.title}" at your esteemed company.

Below are my details and why I am a strong match for this opportunity:

---
Student Details:
Name: {student_profile.get_full_name()}
Email: {student_user.email}
Phone: {student_profile.phone_number or 'N/A'}
Course: {student_profile.course}
Year Level: {student_profile.get_year_level_display()}
Section: {student_profile.section or 'N/A'}
Address: {address}
Skills: {skills}
OJT Hours Completed: {student_profile.ojt_hours_completed} / {student_profile.ojt_hours_required}
CV: {cv_url}

Application Details:
Internship Title: {internship.title}
Company: {internship.company.name}
Match Score: {match_score}/100

Why I am a good fit:
- My course and skills closely match your requirements for this internship.
- I am eager to contribute and learn from your team.
- I have demonstrated responsibility and commitment in my academic and extracurricular activities.

Thank you for considering my application. I am looking forward to the possibility of contributing to your organization and am available for an interview at your convenience.

Best regards,
{student_profile.get_full_name()}
{student_user.email}
{student_profile.phone_number or ''}
"""
            recipient_list = [internship.company.hr_email or internship.company.company_email]
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=student_user.email,  # Use student's updated email as sender
                to=recipient_list,
                reply_to=[student_user.email],
            )
            # Attach CV if available
            if student_profile.cv:
                try:
                    cv_path = student_profile.cv.path
                    cv_name = student_profile.cv.name.split('/')[-1]
                    with open(cv_path, 'rb') as cv_file:
                        email.attach(cv_name, cv_file.read(), student_profile.cv.file.content_type or 'application/octet-stream')
                except Exception:
                    pass
            email.send(fail_silently=True)
            messages.success(request, f'Successfully applied to {internship.title} at {internship.company.name}.')
            return redirect('internship:applications')
        
        # Calculate distance if both have lat/lng
        distance_km = None
        if internship.company.latitude and internship.company.longitude and profile.latitude and profile.longitude:
            from math import radians, sin, cos, sqrt, atan2
            def haversine(lat1, lon1, lat2, lon2):
                R = 6371  # Earth radius in km
                dlat = radians(lat2 - lat1)
                dlon = radians(lon2 - lon1)
                a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                return R * c
            try:
                distance_km = round(haversine(float(internship.company.latitude), float(internship.company.longitude), float(profile.latitude), float(profile.longitude)), 1)
            except Exception:
                distance_km = None
        context = {
            'internship': internship,
            'profile': profile,
            'match_score': internship.get_match_score(profile),
            'distance_km': distance_km,
        }
        return render(request, 'internship/apply.html', context)
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')

@login_required
def company_detail(request, company_id):
    """View company details."""
    company = get_object_or_404(Company, id=company_id)
    
    # Get active internships for this company
    internships = Internship.objects.filter(company=company, is_active=True)
    
    # Get reviews for this company
    reviews = CompanyReview.objects.filter(company=company).order_by('-created_at')
    
    # Calculate average rating
    avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0
    
    context = {
        'company': company,
        'internships': internships,
        'reviews': reviews,
        'avg_rating': avg_rating,
    }
    return render(request, 'internship/company_detail.html', context)

@login_required
def add_company_review(request, company_id):
    """Add a review for a company."""
    if not request.user.is_student:
        messages.error(request, 'Only students can review companies.')
        return redirect('dashboard:home')
    
    company = get_object_or_404(Company, id=company_id)
    
    try:
        profile = request.user.student_profile
        
        # Check if student has already reviewed this company
        if CompanyReview.objects.filter(student=profile, company=company).exists():
            messages.warning(request, 'You have already reviewed this company.')
            return redirect('internship:company_detail', company_id=company.id)
        
        if request.method == 'POST':
            form = CompanyReviewForm(request.POST)
            if form.is_valid():
                review = form.save(commit=False)
                review.student = profile
                review.company = company
                review.save()
                messages.success(request, 'Review submitted successfully.')
                return redirect('internship:company_detail', company_id=company.id)
        else:
            form = CompanyReviewForm()
        
        return render(request, 'internship/add_review.html', {'form': form, 'company': company})
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')

# Coordinator views
@login_required
def company_list(request):
    """View list of companies."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only OJT Coordinators can access company management.')
        return redirect('dashboard:home')
    
    companies = Company.objects.all().order_by('name')
    
    # Filter by status if specified
    status = request.GET.get('status')
    if status in [Company.Status.ACTIVE, Company.Status.INACTIVE]:
        companies = companies.filter(status=status)
    
    # Pagination
    paginator = Paginator(companies, 10)  # Show 10 companies per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Count active companies (regardless of pagination/filter)
    active_companies_count = Company.objects.filter(status=Company.Status.ACTIVE).count()
    
    context = {
        'companies': page_obj,
        'status_filter': status,
        'active_companies_count': active_companies_count,
    }
    return render(request, 'internship/company_list.html', context)

@login_required
def add_company(request):
    """Add a new company."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only OJT Coordinators can add companies.')
        return redirect('dashboard:home')
    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            company = form.save(commit=False)
            company.added_by = request.user
            company.save()
            messages.success(request, 'Company added successfully.')
            return redirect('internship:companies')
    else:
        form = CompanyForm()
    return render(request, 'internship/add_company.html', {'form': form})

@login_required
def edit_company(request, company_id):
    """Edit a company."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only OJT Coordinators can edit companies.')
        return redirect('dashboard:home')
    company = get_object_or_404(Company, id=company_id)
    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            company = form.save(commit=False)
            # Parse and set latitude/longitude from POST if present (handle blank, string, float)
            lat_val = request.POST.get('latitude', '').strip()
            lng_val = request.POST.get('longitude', '').strip()
            company.latitude = float(lat_val) if lat_val else None
            company.longitude = float(lng_val) if lng_val else None
            company.save()
            form.save_m2m()
            messages.success(request, 'Company updated successfully.')
            return redirect('internship:companies')
    else:
        form = CompanyForm(instance=company)
    return render(request, 'internship/edit_company.html', {'form': form, 'company': company})

@login_required
def toggle_company_status(request, company_id):
    """Toggle company status between active and inactive."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only OJT Coordinators can manage companies.')
        return redirect('dashboard:home')
    
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        # Toggle status
        if company.status == Company.Status.ACTIVE:
            company.status = Company.Status.INACTIVE
            status_msg = 'deactivated'
        else:
            company.status = Company.Status.ACTIVE
            status_msg = 'activated'
        
        company.save()
        messages.success(request, f'Company "{company.name}" has been {status_msg}.')
        return redirect('internship:companies')
    
    return render(request, 'internship/confirm_toggle_status.html', {'company': company})

@login_required
def internship_list(request):
    """View list of internships."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only OJT Coordinators can access internship management.')
        return redirect('dashboard:home')
    
    internships = Internship.objects.all().order_by('-created_at')
    
    # Filter by company if specified
    company_id = request.GET.get('company')
    if company_id:
        internships = internships.filter(company_id=company_id)
    
    # Filter by status if specified
    is_active = request.GET.get('is_active')
    if is_active is not None:
        is_active = is_active.lower() == 'true'
        internships = internships.filter(is_active=is_active)
    
    # Pagination
    paginator = Paginator(internships, 10)  # Show 10 internships per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate slots for the first internship on the current page
    first_internship_slots = 0
    if page_obj and page_obj.object_list:
        first_internship = page_obj.object_list[0]
        first_internship_slots = getattr(first_internship, 'slots_available', 0)

    context = {
        'internships': page_obj,
        'companies': Company.objects.filter(status=Company.Status.ACTIVE),
        'company_filter': company_id,
        'status_filter': is_active,
        'first_internship_slots': first_internship_slots,
    }
    return render(request, 'internship/internship_list.html', context)

@login_required
def add_internship(request):
    """Add a new internship."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only OJT Coordinators can add internships.')
        return redirect('dashboard:home')
    
    import json
    if request.method == 'POST':
        post_data = request.POST.copy()
        # Handle recommended_courses from hidden field (single or multi)
        course_val = post_data.get('course')
        if course_val:
            post_data.setlist('recommended_courses', [course_val] if ',' not in course_val else course_val.split(','))
        # Handle required_skills from skills_json
        skills_json = post_data.get('skills_json')
        skill_ids = []
        custom_skill_names = []
        if skills_json:
            try:
                skills = json.loads(skills_json)
                for s in skills:
                    if s.get('id'):
                        skill_ids.append(str(s['id']))
                    elif s.get('name'):
                        custom_skill_names.append(s['name'])
            except Exception:
                pass
        if skill_ids:
            post_data.setlist('required_skills', skill_ids)
        # Add custom skills to free_skills (comma separated)
        if custom_skill_names:
            post_data['free_skills'] = ','.join(custom_skill_names)
        form = InternshipForm(post_data)
        if form.is_valid():
            internship = form.save()
            messages.success(request, 'Internship added successfully.')
            return redirect('/internship/internships/')
    else:
        form = InternshipForm()
    # Build course_skill_map for JS
    course_skill_map = {}
    for course in Course.objects.all():
        skills = Skill.objects.filter(course=course).values('id', 'name')
        course_skill_map[str(course.id)] = list(skills)
    context = {
        'form': form,
        'companies': Company.objects.filter(status=Company.Status.ACTIVE),
        'courses': Course.objects.all(),
        'skills': Skill.objects.all(),
        'course_skill_map': course_skill_map,
    }
    return render(request, 'internship/add_internship.html', context)

@login_required
def internship_detail(request, internship_id):
    """View internship details."""
    internship = get_object_or_404(Internship, id=internship_id)
    
    # Get applications for this internship
    applications = Application.objects.filter(internship=internship).order_by('-match_score')
    
    context = {
        'internship': internship,
        'applications': applications,
    }
    return render(request, 'internship/internship_detail.html', context)

@login_required
def edit_internship(request, internship_id):
    """Edit an internship."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only OJT Coordinators can edit internships.')
        return redirect('dashboard:home')
    
    internship = get_object_or_404(Internship, id=internship_id)
    
    import json
    if request.method == 'POST':
        post_data = request.POST.copy()
        # Handle required_skills from skills_json
        skills_json = post_data.get('skills_json')
        skill_ids = []
        custom_skill_names = []
        if skills_json:
            try:
                skills = json.loads(skills_json)
                for s in skills:
                    if s.get('id'):
                        skill_ids.append(str(s['id']))
                    elif s.get('name'):
                        custom_skill_names.append(s['name'])
            except Exception:
                pass
        if skill_ids:
            post_data.setlist('required_skills', skill_ids)
        # Add custom skills to free_skills (comma separated)
        if custom_skill_names:
            post_data['free_skills'] = ','.join(custom_skill_names)
        # Do NOT override recommended_courses; let Django handle the multi-select
        form = InternshipForm(post_data, instance=internship)
        if form.is_valid():
            internship = form.save()
            messages.success(request, 'Internship updated successfully.')
            return redirect('/internship/internships/')
    else:
        form = InternshipForm(instance=internship)
    # Build course_skill_map for JS
    course_skill_map = {}
    for course in Course.objects.all():
        skills = Skill.objects.filter(course=course).values('id', 'name')
        course_skill_map[str(course.id)] = list(skills)
    context = {
        'form': form,
        'internship': internship,
        'companies': Company.objects.filter(status=Company.Status.ACTIVE),
        'courses': Course.objects.all(),
        'skills': Skill.objects.all(),
        'course_skill_map': course_skill_map,
    }
    return render(request, 'internship/edit_internship.html', context)

@login_required
def toggle_internship_status(request, internship_id):
    """Toggle internship status between active and inactive."""
    if not request.user.is_coordinator:
        messages.error(request, 'Only OJT Coordinators can manage internships.')
        return redirect('dashboard:home')
    
    internship = get_object_or_404(Internship, id=internship_id)
    
    if request.method == 'POST':
        # Toggle status
        internship.is_active = not internship.is_active
        internship.save()
        
        status_msg = 'activated' if internship.is_active else 'deactivated'
        messages.success(request, f'Internship "{internship.title}" has been {status_msg}.')
        return redirect('internship:internships')
    
    return render(request, 'internship/confirm_toggle_internship_status.html', {'internship': internship})

@login_required
def api_skills_by_course(request, course_id):
    """API endpoint to get skills by course."""
    course = get_object_or_404(Course, id=course_id)
    skills = Skill.objects.filter(course=course)
    
    # Convert skills to JSON
    skills_data = [{'id': skill.id, 'name': skill.name} for skill in skills]
    
from django.shortcuts import render

# Create your views here.

@login_required
def application_detail(request, application_id):
    """View details of a student's internship application. Allow student to update status."""
    application = get_object_or_404(Application, id=application_id)
    can_update = False
    if request.user.is_student and application.student.user == request.user:
        can_update = True
    if request.method == 'POST' and can_update:
        form = ApplicationStatusUpdateForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            messages.success(request, 'Application status updated!')
            return redirect('internship:application_detail', application_id=application.id)
    else:
        form = ApplicationStatusUpdateForm(instance=application) if can_update else None
    return render(request, 'internship/application_detail.html', {
        'application': application,
        'status_form': form,
        'can_update': can_update,
    })
