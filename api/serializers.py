from rest_framework import serializers
from interviewConversation.models import InterviewConversation
from job.models import  Job
from candidate.models import Candidate


class InterviewConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewConversation
        fields = '__all__'


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = '__all__'
