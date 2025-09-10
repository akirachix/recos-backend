from rest_framework import serializers
from interview.models import Interview
from interviewConversation.models import InterviewConversation
from job.models import  Job
from candidate.models import Candidate
from ai_reports.models import AIReport

class InterviewSerializer(serializers.ModelSerializer):
    interview_link = serializers.CharField(read_only=True)
    google_event_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Interview
        fields = [
            "id",
            "scheduled_at",
            "status",
            "interview_link",
            "google_event_id",
            "created_at",
            "updated_at",
        ]



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

class AIReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIReport
        fields = '__all__'
        read_only_fields = ['report_id', 'created_at', 'updated_at']

class AIReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIReport
        fields = [
            'conversation_id',
            'skill_match_score',
            'final_match_score',
            'strengths',
            'weaknesses',
            'overall_recommendation',
            'skills_breakdown',
            'initial_analysis',
            'performance_analysis',
        ]
