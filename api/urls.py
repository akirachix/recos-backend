
from rest_framework.routers import DefaultRouter
from .views import InterviewConversationViewSet, JobViewSet, CandidateViewSet, AIReportViewSet, InterviewViewSet
from django.urls import path,include
from . import views


router = DefaultRouter()
router.register(r'interview_conversations', InterviewConversationViewSet)
router.register(r'jobs', JobViewSet)
router.register(r'candidates', CandidateViewSet)
router.register(r'interview', InterviewViewSet)
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
    path('users/', views.RecruiterListView.as_view(),name='recruiter_list'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('verify-reset-code/', views.verify_reset_code, name='verify_reset_code'), 
    path('sync/all-data/', views.sync_all_data, name='sync_all_data'),
]