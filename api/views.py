from django.shortcuts import render

from rest_framework import viewsets
from interviewConversation.models import InterviewConversation
from job.models import Job
from candidate.models import Candidate
from .serializers import InterviewConversationSerializer, JobSerializer, CandidateSerializer

class InterviewConversationViewSet(viewsets.ModelViewSet):
    queryset = InterviewConversation.objects.all()
    serializer_class = InterviewConversationSerializer

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
