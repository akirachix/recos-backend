from django.urls import path, include

urlpatterns = [
    path('interview/', include('interview.urls')),
]