from rest_framework import viewsets
from interview.models import Interview
from .serializers import InterviewSerializer

class InterviewViewSet(viewsets.ModelViewSet):
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer