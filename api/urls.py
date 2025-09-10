from rest_framework.routers import DefaultRouter
from .views import InterviewConversationViewSet, JobViewSet, CandidateViewSet
from django.urls import path,include

router = DefaultRouter()
router.register(r'interview_conversations', InterviewConversationViewSet)
router.register(r'jobs', JobViewSet)
router.register(r'candidates', CandidateViewSet)


urlpatterns = [
    path('', include(router.urls))  
]