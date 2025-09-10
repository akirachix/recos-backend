from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIReportViewSet

router = DefaultRouter()
router.register(r'ai-reports', AIReportViewSet, basename='ai-report')

urlpatterns = [
    path('', include(router.urls)),
]