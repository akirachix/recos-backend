
from rest_framework.routers import DefaultRouter
from .views import InterviewConversationViewSet, JobViewSet, CandidateViewSet, InterviewViewSet
from django.urls import path,include

router = DefaultRouter()
router.register(r'interview_conversations', InterviewConversationViewSet)
router.register(r'jobs', JobViewSet)
router.register(r'candidates', CandidateViewSet)
router.register(r'interview', InterviewViewSet)


urlpatterns = [
    path('', include(router.urls)),
]