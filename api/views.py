from rest_framework import viewsets, status
from rest_framework.response import Response
from interviewConversation.models import InterviewConversation
from job.models import Job
from candidate.models import Candidate
from interview.models import Interview
from .serializers import (
    InterviewConversationSerializer, 
    JobSerializer, 
    CandidateSerializer, 
    InterviewSerializer
)
from interview.utils import create_google_calendar_event

class InterviewConversationViewSet(viewsets.ModelViewSet):
    queryset = InterviewConversation.objects.all()
    serializer_class = InterviewConversationSerializer

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer

class InterviewViewSet(viewsets.ModelViewSet):
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview = serializer.save()

   
        event_id, hangout_link = create_google_calendar_event(interview)
        interview.google_event_id = event_id
        interview.interview_link = hangout_link
        interview.save()
        output_serializer = self.get_serializer(interview)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)