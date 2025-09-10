from django.shortcuts import render

from rest_framework import viewsets
from interviewConversation.models import InterviewConversation
from .serializers import InterviewConversationSerializer

class InterviewConversationViewSet(viewsets.ModelViewSet):
    queryset = InterviewConversation.objects.all()
    serializer_class = InterviewConversationSerializer
