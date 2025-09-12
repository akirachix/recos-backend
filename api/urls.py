
from rest_framework.routers import DefaultRouter
from .views import InterviewConversationViewSet, JobViewSet, CandidateViewSet, AIReportViewSet, InterviewViewSet
from django.urls import path,include
from . import views


router = DefaultRouter()
router.register(r'interview_conversations', InterviewConversationViewSet, basename='interview_conversation')
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'candidates', CandidateViewSet, basename='candidate')
router.register(r'interview', InterviewViewSet, basename='interview')
router.register(r'ai-reports', AIReportViewSet, basename='ai-report')



urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.RecruiterRegistrationView.as_view(), name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-odoo/', views.verify_odoo_account, name='verify_odoo_account'),
    path('odoo-credentials/', views.add_odoo_credentials, name='add_odoo_credentials'),
    path('odoo-credentials/list/', views.get_odoo_credentials, name='get_odoo_credentials'),
    path('companies/', views.get_companies, name='get_companies'),
    path('users/', views.RecruiterListView.as_view(),name='recruiter_list'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('verify-reset-code/', views.verify_reset_code, name='verify_reset_code'), 
    path('sync/all-data/', views.sync_all_data, name='sync_all_data'),
    path('jobs/<int:job_id>/candidates/', views.get_candidates_by_job, name='get_candidates_by_job'),
    path('sync/jobs/company/<int:company_id>/', views.sync_jobs_for_company, name='sync_jobs_for_company'),
    path('sync/candidates/job/<int:job_id>/', views.sync_candidates_for_job, name='sync_candidates_for_job'),
    path('companies/<int:company_id>/jobs/', views.get_jobs_by_company, name='get_jobs_by_company'),
    path('sync/jobs/user/', views.sync_jobs_for_user, name='sync_jobs_for_user'),
    path('debug/companies/', views.debug_companies, name='debug_companies'),
    path('verify/companies/', views.verify_companies, name='verify_companies'),
    path('sync/companies/', views.sync_companies, name='sync_companies'),
    path('debug/db-state/', views.debug_db_state, name='debug_db_state'),
    path('reset/company-sequence/', views.reset_company_sequence, name='reset_company_sequence'),
    path('sync/jobs/handle-duplicates/', views.sync_jobs_handle_duplicates, name='sync_jobs_handle_duplicates'),
]

