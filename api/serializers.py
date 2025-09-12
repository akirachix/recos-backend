from rest_framework import serializers
from interview.models import Interview
from interviewConversation.models import InterviewConversation
from job.models import  Job
from candidate.models import Candidate
from django.contrib.auth import get_user_model
from users.models import OdooCredentials
from companies.models import Company
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
    company_name = serializers.CharField(source='company.company_name', read_only=True)
    company_id = serializers.IntegerField(source='company.company_id', read_only=True)
    
    class Meta:
        model = Job
        fields = [
            'job_id', 
            'company',  
            'company_name', 
            'company_id',
            'job_title', 
            'job_description', 
            'generated_job_summary', 
            'state', 
            'posted_at', 
            'expired_at', 
            'created_at'
        ]
        extra_kwargs = {
            'company': {'required': True}  
        }

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = '__all__'

Recruiter = get_user_model()

class RecruiterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = Recruiter
        fields = ['id', 'first_name', 'last_name', 'email', 'password', 'image', 'created_at', 'updated_at']
        extra_kwargs = {'password': {'write_only': True}}
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Recruiter(**validated_data)
        user.set_password(password)
        user.save()
        return user

class OdooCredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OdooCredentials
        fields = ['credentials_id', 'odoo_user_id', 'email_address', 'db_name', 'db_url', 'created_at', 'updated_at']
        read_only_fields = ['credentials_id', 'created_at', 'updated_at']


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


class CompanySerializer(serializers.ModelSerializer):
    recruiter_email = serializers.CharField(source='recruiter.email', read_only=True)
    recruiter_id = serializers.IntegerField(source='recruiter.id', read_only=True)
    
    class Meta:
        model = Company
        fields = [
            'company_id', 
            'company_name', 
            'recruiter', 
            'recruiter_email',
            'recruiter_id',
            'odoo_credentials', 
            'is_active', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['recruiter', 'created_at', 'updated_at']