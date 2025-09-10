from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Interview
from api.serializers import InterviewSerializer
from .utils import create_google_calendar_event

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