from rest_framework.routers import DefaultRouter
from .views import (
    InterviewConversationViewSet,
    JobViewSet,
    CandidateViewSet,
    AIReportViewSet,
    InterviewViewSet,
    SyncCandidatesForCompanyView,
    download_candidate_attachment,
)
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register(r'interview_conversations', InterviewConversationViewSet, basename='interview_conversation')
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'candidates', CandidateViewSet, basename='candidate')
router.register(r'interview', InterviewViewSet, basename='interview')
router.register(r'ai-reports', AIReportViewSet, basename='ai-report')

urlpatterns = [
    path('', include(router.urls)),
    path('', views.api_root, name='api_root'),
    path('register/', views.RecruiterRegistrationView.as_view(), name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-odoo/', views.verify_odoo_account, name='verify_odoo_account'),
    path('odoo-credentials/', views.add_odoo_credentials, name='add_odoo_credentials'),
    path('odoo-credentials/list/', views.get_odoo_credentials, name='get_odoo_credentials'),
    path('companies/', views.get_companies, name='get_companies'),
    path('users/', views.RecruiterListView.as_view(), name='recruiter_list'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset_password'),
    path('verify-reset-code/', views.VerifyCodeView.as_view(), name='verify_reset_code'),
    path('jobs/<int:job_id>/candidates/', views.get_candidates_by_job, name='get_candidates_by_job'),
    path('sync/jobs/company/<int:company_id>/', views.sync_jobs_for_company, name='sync_jobs_for_company'),
    path('sync/jobs/handle-duplicates/', views.sync_jobs_handle_duplicates, name='sync_jobs_handle_duplicates'),
    path('sync/candidates/job/<int:job_id>/', views.sync_candidates_for_job, name='sync_candidates_for_job'),
    path('sync/candidates/company/<int:company_id>/', views.sync_candidates_for_company, name='sync_candidates_for_company'),
    path('sync/candidates/all/', views.sync_all_candidates, name='sync_all_candidates'),
    path('sync/candidates/company/<int:company_id>/', SyncCandidatesForCompanyView.as_view(), name='sync_candidates_for_company'),
    path('companies/<int:company_id>/jobs/', views.get_jobs_by_company, name='get_jobs_by_company'),
    path('candidates/<int:candidate_id>/attachments/', views.get_candidate_attachments, name='get_candidate_attachments'),
    path('sync/jobs/user/', views.sync_jobs_for_user, name='sync_jobs_for_user'),
    path('candidates/<int:candidate_id>/attachments/download/<int:attachment_id>/', views.download_candidate_attachment, name='download_candidate_attachment'),
    path('sync/candidates/<int:candidate_id>/attachments/', views.sync_candidate_attachments, name='sync_candidate_attachments'),
    path('candidate_attachments/<int:attachment_id>/download/', download_candidate_attachment, name='download_candidate_attachment'),
    path('interviews/create/', views.create_interview, name='create-interview'),
    path('interviews/<int:interview_id>/create-calendar-event/', views.create_interview_event, name='create-calendar-event'),
    path('interviews/<int:interview_id>/analytics/', views.get_interview_analytics, name='get-interview-analytics'),
    path('auth/google/initiate/', views.google_auth_initiate, name='google_auth_initiate'),
    path('auth/google/callback/', views.google_auth_callback, name='google_auth_callback'),
    path('api/auth/google/callback/', views.google_auth_callback, name='api_google_auth_callback'),
    path('update-profile/', views.update_profile, name='update-profile'),
    path('delete-account/', views.delete_account, name='delete-account'),
]
