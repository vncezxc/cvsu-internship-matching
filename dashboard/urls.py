        # Download full edited required document (HTML)
    
    # Generalized full document editor for required document
from django.urls import path
from . import views
from . import views_edit_moa
from . import views_download_moa
from . import views_onlyoffice_callback

    
app_name = 'dashboard'

urlpatterns = [
    # Home dashboards
    path('', views.dashboard_redirect, name='home'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('student/documents/', views.student_documents_view, name='student_documents'),
    path('adviser/', views.adviser_dashboard, name='adviser_dashboard'),
    path('coordinator/', views.coordinator_dashboard, name='coordinator_dashboard'),

    # Adviser document review
    path('adviser/documents/', views.adviser_documents_review, name='adviser_documents_review'),

    # DTR Submission and Review
    path('student/dtr/submit/', views.submit_dtr, name='submit_dtr'),
    path('adviser/dtr/', views.adviser_dtr_list, name='adviser_dtr_list'),
    path('adviser/dtr/<int:dtr_id>/review/', views.review_dtr, name='review_dtr'),

    # Student management (for advisers)
    path('students/', views.student_list, name='student_list'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
    path('students/<int:student_id>/update-status/', views.update_student_status, name='update_student_status'),
    path('students/<int:student_id>/update-hours/', views.update_ojt_hours, name='update_ojt_hours'),

    # Reports
    path('reports/', views.reports_dashboard, name='reports'),
    path('reports/generate/student-list/', views.generate_student_list, name='generate_student_list'),
    path('reports/generate/ojt-tracking/', views.generate_ojt_tracking, name='generate_ojt_tracking'),
    path('reports/<int:report_id>/download/', views.download_report, name='download_report'),
    path('reports/generate/student-list/pdf/', views.generate_student_list_pdf, name='generate_student_list_pdf'),
    path('reports/generate/ojt-tracking/pdf/', views.generate_ojt_tracking_pdf, name='generate_ojt_tracking_pdf'),
    path('reports/generate/company-list/pdf/', views.generate_company_list_pdf, name='generate_company_list_pdf'),
    path('reports/generate/application-summary/pdf/', views.generate_application_summary_pdf, name='generate_application_summary_pdf'),

    # Statistics API (for charts)
    path('api/statistics/', views.api_statistics, name='api_statistics'),

    # MOA Edit
    path('required-documents/<int:doc_id>/onlyoffice-callback/', views_onlyoffice_callback.onlyoffice_callback, name='onlyoffice_callback'),

    path('student/documents/moa/edit/<int:doc_id>/', views_edit_moa.edit_moa_view, name='edit_moa'),
    path('student/documents/moa/download/<int:doc_id>/', views_download_moa.download_edited_moa, name='download_edited_moa'),

    # Required Documents management (coordinator only)
    path('required-documents/', views.required_documents_list, name='required_documents_list'),
    path('required-documents/add/', views.add_required_document, name='add_required_document'),
    path('required-documents/<int:doc_id>/edit/', views.edit_required_document, name='edit_required_document'),
    path('required-documents/<int:doc_id>/delete/', views.delete_required_document, name='delete_required_document'),

    # Student document upload
    path('student/documents/upload/<int:doc_id>/', views.upload_student_document, name='upload_student_document'),

    # Coordinator upload/update/delete student document
    path('coordinator/documents/upload/<int:student_id>/<int:doc_id>/', views.coordinator_upload_student_document, name='coordinator_upload_student_document'),
    path('coordinator/documents/delete/<int:student_id>/<int:doc_id>/', views.coordinator_delete_student_document, name='coordinator_delete_student_document'),

    # Coordinator-level documents overview
    path('required-documents/<int:doc_id>/download-edited/', views_download_moa.download_edited_required_document, name='download_edited_required_document'),
    path('required-documents/<int:doc_id>/edit-full/', views_edit_moa.edit_required_document_full_view, name='edit_required_document_full'),
    path('coordinator/documents-overview/', views.coordinator_documents_overview, name='coordinator_documents_overview'),

    # Alias for student_documents_view to match template usage
    path('student/documents/', views.student_documents_view, name='student_documents_view'),
]