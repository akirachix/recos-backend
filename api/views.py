from rest_framework import viewsets
from job.models import Job
from candidate.models import Candidate
from .serializers import  JobSerializer, CandidateSerializer

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
