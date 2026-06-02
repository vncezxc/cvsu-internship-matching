from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Company, Internship, Application, CompanyReview
from .matching import score_internship
from accounts.models import StudentProfile, Skill, Course
from .forms import InternshipForm
from .forms import CompanyForm, CompanyReviewForm, ApplicationStatusUpdateForm, CustomCompanyInternshipForm
from django.db import models
import re

# Create your views here.

def parse_lat_lng_from_link(link):
    value = (link or "").strip()
    if not value:
        return None

    patterns = [
        r"^([\-\d.]+)\s*,\s*([\-\d.]+)$",
        r"@([\-\d.]+),([\-\d.]+),",
        r"!3d([\-\d.]+)!4d([\-\d.]+)",
        r"!2d([\-\d.]+)!3d([\-\d.]+)",
        r"[?&]center=([\-\d.]+),([\-\d.]+)",
        r"[?&]destination=([\-\d.]+),([\-\d.]+)",
        r"[?&]origin=([\-\d.]+),([\-\d.]+)",
        r"[?&]point=([\-\d.]+),([\-\d.]+)",
        r"[?&]q=([\-\d.]+),([\-\d.]+)",
        r"[?&]query=([\-\d.]+),([\-\d.]+)",
        r"[?&]ll=([\-\d.]+),([\-\d.]+)",
        r"[?&]cp=([\-\d.]+)~([\-\d.]+)",
        r"#map=\d+/([\-\d.]+)/([\-\d.]+)",
        r"mlat=([\-\d.]+)&mlon=([\-\d.]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            if "!2d" in pattern:
                lat_val, lng_val = match.group(2), match.group(1)
            else:
                lat_val, lng_val = match.group(1), match.group(2)
            try:
                lat = float(lat_val)
                lng = float(lng_val)
            except ValueError:
                continue
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return lat, lng

    numeric_values = re.findall(r"[\-+]?\d{1,3}(?:\.\d+)?", value)
    for idx in range(len(numeric_values) - 1):
        try:
            lat = float(numeric_values[idx])
            lng = float(numeric_values[idx + 1])
        except ValueError:
            continue
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng

    return None

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
        
        # Get all active and approved internships
        internships = Internship.objects.filter(
            is_active=True,
            approval_status=Internship.ApprovalStatus.APPROVED,
            company__approval_status=Company.ApprovalStatus.APPROVED
        )

        # Filter by course if specified (recommended_courses is a M2M field)
        if profile.course:
            internships = internships.filter(recommended_courses=profile.course)

        # Calculate match scores for each internship
        matches = []
        for internship in internships:
            # Skip internships the student has already applied to
            if Application.objects.filter(student=profile, internship=internship).exists():
                continue

            match_result = score_internship(profile, internship)
            if match_result["score"] > 0:
                matches.append({
                    'internship': internship,
                    'score': match_result["score"],
                    'distance_km': match_result["distance_km"],
                    'tech_pct': match_result["tech_pct"],
                    'soft_pct': match_result["soft_pct"],
                    'course_pct': match_result["course_pct"],
                    'map_pct': match_result["map_pct"],
                })

        # Sort by match score (highest first)
        matches.sort(key=lambda x: x['score'], reverse=True)

        best_match = matches[0] if matches else None
        other_matches = matches[1:] if len(matches) > 1 else []

        # Pagination for other matches
        paginator = Paginator(other_matches, 10)  # Show 10 per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        recommendations = []
        if not matches:
            recommendations = Internship.objects.filter(
                is_active=True,
                approval_status=Internship.ApprovalStatus.APPROVED,
                company__approval_status=Company.ApprovalStatus.APPROVED
            )
            if profile.course:
                recommendations = recommendations.filter(recommended_courses=profile.course)
            recommendations = recommendations.exclude(
                applications__student=profile
            ).order_by('-created_at')[:3]

        context = {
            'best_match': best_match,
            'matches': page_obj,
            'matches_count': len(matches),
            'profile': profile,
            'recommendations': recommendations,
        }
        return render(request, 'internship/matches.html', context)
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')


@login_required
def submit_custom_internship(request):
    """Student submits a custom company and internship for adviser approval."""
    if not request.user.is_student:
        messages.error(request, 'Only students can submit custom internships.')
        return redirect('dashboard:home')

    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.warning(request, 'Please complete your profile first.')
        return redirect('accounts:edit_profile')

    if request.method == 'POST':
        form = CustomCompanyInternshipForm(request.POST, request.FILES)
        if form.is_valid():
            lat_val = (request.POST.get('latitude') or '').strip()
            lng_val = (request.POST.get('longitude') or '').strip()
            try:
                latitude = float(lat_val) if lat_val else None
                longitude = float(lng_val) if lng_val else None
            except ValueError:
                latitude = None
                longitude = None

            company = Company.objects.create(
                name=form.cleaned_data['company_name'],
                description=form.cleaned_data['company_description'],
                company_type=form.cleaned_data['company_type'],
                company_email=form.cleaned_data['company_email'],
                hr_email=form.cleaned_data['hr_email'],
                phone_number=form.cleaned_data['phone_number'],
                street=form.cleaned_data['street'],
                barangay=form.cleaned_data['barangay'],
                city=form.cleaned_data['city'],
                province=form.cleaned_data['province'],
                location_link=form.cleaned_data.get('location_link') or '',
                latitude=latitude,
                longitude=longitude,
                status=Company.Status.INACTIVE,
                approval_status=Company.ApprovalStatus.PENDING,
                added_by=request.user,
            )

            internship = Internship.objects.create(
                company=company,
                title=form.cleaned_data['internship_title'],
                description=form.cleaned_data['internship_description'],
                is_active=False,
                slots_available=1,
                approval_status=Internship.ApprovalStatus.PENDING,
                submitted_by=profile,
                acceptance_letter=form.cleaned_data['acceptance_letter'],
                job_description=form.cleaned_data['job_description'],
            )

            if profile.course:
                internship.recommended_courses.add(profile.course)

            messages.success(request, 'Custom company and internship submitted for adviser review.')
            return redirect('internship:custom_submission')
    else:
        form = CustomCompanyInternshipForm()

    submissions = Internship.objects.filter(submitted_by=profile).select_related('company').order_by('-created_at')

    return render(request, 'internship/custom_submission.html', {
        'form': form,
        'profile': profile,
        'submissions': submissions,
    })

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
            import logging
            logger = logging.getLogger(__name__)
            from django.conf import settings
            logger.info(f"EMAIL_BACKEND in use: {getattr(settings, 'EMAIL_BACKEND', None)}")
            # Force SendGrid: use DEFAULT_FROM_EMAIL as sender
            from django.conf import settings
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'internmatchingcvsu@gmail.com'),
                to=recipient_list,
                reply_to=[student_user.email],
            )
            # Attach CV if available
            if student_profile.cv:
                try:
                    cv_name = student_profile.cv.name.split('/')[-1]
                    student_profile.cv.open('rb')
                    email.attach(cv_name, student_profile.cv.read(), student_profile.cv.file.content_type or 'application/octet-stream')
                    student_profile.cv.close()
                except Exception as e:
                    logger.error(f"Error attaching CV: {e}")
            try:
                email.send(fail_silently=False)
                logger.info(f"Internship application email sent to: {recipient_list}")
            except Exception as e:
                logger.error(f"Error sending internship application email: {e}")
                messages.error(request, f"Failed to send application email: {e}")
                return redirect('internship:applications')
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
    company_queryset = Company.objects.all()
    if request.user.is_student:
        company_queryset = company_queryset.filter(approval_status=Company.ApprovalStatus.APPROVED)
    company = get_object_or_404(company_queryset, id=company_id)
    
    # Get active internships for this company
    internships = Internship.objects.filter(
        company=company,
        is_active=True,
        approval_status=Internship.ApprovalStatus.APPROVED
    )
    
    # Get reviews for this company
    reviews = CompanyReview.objects.filter(company=company).order_by('-created_at')
    
    # Calculate average rating
    avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0

    has_review = False
    review_form = None
    if request.user.is_authenticated and request.user.is_student:
        try:
            profile = request.user.student_profile
            has_review = CompanyReview.objects.filter(student=profile, company=company).exists()
            if not has_review:
                review_form = CompanyReviewForm()
        except StudentProfile.DoesNotExist:
            review_form = None
    
    context = {
        'company': company,
        'internships': internships,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_form': review_form,
        'has_review': has_review,
    }
    return render(request, 'internship/company_detail.html', context)

@login_required
@require_POST
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
        
        form = CompanyReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.student = profile
            review.company = company
            review.save()
            messages.success(request, 'Review submitted successfully.')
        else:
            messages.error(request, 'Please correct the review form and try again.')
        return redirect('internship:company_detail', company_id=company.id)
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
            lat_val = (request.POST.get('latitude') or '').strip()
            lng_val = (request.POST.get('longitude') or '').strip()
            latitude = None
            longitude = None

            try:
                latitude = float(lat_val) if lat_val else None
                longitude = float(lng_val) if lng_val else None
            except ValueError:
                latitude = None
                longitude = None

            if latitude is None or longitude is None:
                parsed = parse_lat_lng_from_link(form.cleaned_data.get('location_link'))
                if parsed:
                    latitude, longitude = parsed

            company.latitude = latitude
            company.longitude = longitude
            if not company.location_link and latitude is not None and longitude is not None:
                company.location_link = (
                    "https://www.openstreetmap.org/?mlat="
                    f"{latitude:.6f}&mlon={longitude:.6f}#map=18/{latitude:.6f}/{longitude:.6f}"
                )
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
            latitude = None
            longitude = None
            try:
                latitude = float(lat_val) if lat_val else None
                longitude = float(lng_val) if lng_val else None
            except ValueError:
                latitude = None
                longitude = None

            if latitude is None or longitude is None:
                parsed = parse_lat_lng_from_link(form.cleaned_data.get('location_link'))
                if parsed:
                    latitude, longitude = parsed

            company.latitude = latitude
            company.longitude = longitude
            if not company.location_link and latitude is not None and longitude is not None:
                company.location_link = (
                    "https://www.openstreetmap.org/?mlat="
                    f"{latitude:.6f}&mlon={longitude:.6f}#map=18/{latitude:.6f}/{longitude:.6f}"
                )
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
@require_POST
def delete_company(request, company_id):
    if not request.user.is_coordinator:
        messages.error(request, 'Only OJT Coordinators can delete companies.')
        return redirect('dashboard:home')

    company = get_object_or_404(Company, id=company_id)
    company.delete()
    messages.success(request, 'Company deleted successfully.')
    return redirect('internship:companies')

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
    # Build course_skill_map for JS (include global skills)
    course_skill_map = {}
    global_skills = list(Skill.objects.filter(course__isnull=True).values('id', 'name'))
    for course in Course.objects.all():
        skills = Skill.objects.filter(course=course).values('id', 'name')
        course_skill_map[str(course.id)] = list(skills) + global_skills
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
    # Build course_skill_map for JS (include global skills)
    course_skill_map = {}
    global_skills = list(Skill.objects.filter(course__isnull=True).values('id', 'name'))
    for course in Course.objects.all():
        skills = Skill.objects.filter(course=course).values('id', 'name')
        course_skill_map[str(course.id)] = list(skills) + global_skills
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
