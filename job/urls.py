from rest_framework.routers import DefaultRouter
from .views import JobViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r'jobs', JobViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
