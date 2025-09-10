from rest_framework import serializers
from interviewConversation.models import InterviewConversation
from job.models import  Job
from candidate.models import Candidate
from django.contrib.auth import get_user_model
from users.models import OdooCredentials
from companies.models import Company

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


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['company_id', 'company_name', 'created_at', 'updated_at']
        read_only_fields = ['company_id', 'created_at', 'updated_at']

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

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['company_id', 'company_name', 'created_at', 'updated_at']
        read_only_fields = ['company_id', 'created_at', 'updated_at']