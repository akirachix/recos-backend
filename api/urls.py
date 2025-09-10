from rest_framework.routers import DefaultRouter
from .views import InterviewConversationViewSet
from django.urls import path,include

router = DefaultRouter()
router.register(r'interview_conversations', InterviewConversationViewSet)

urlpatterns = [
    path('', include(router.urls))
]
