from rest_framework import serializers
from interview.models import Interview
from interviewConversation.models import InterviewConversation
from job.models import Job
from candidate.models import Candidate, CandidateAttachment
from users.models import OdooCredentials, Recruiter
from companies.models import Company
from ai_reports.models import AIReport

class CandidateAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    file_type_display = serializers.SerializerMethodField()

    class Meta:
        model = CandidateAttachment
        fields = [
            'attachment_id', 'candidate', 'name', 'original_filename',
            'file_url', 'download_url', 'preview_url', 'file_type',
            'file_type_display', 'file_size', 'sync_status', 'created_at'
        ]
        read_only_fields = ['attachment_id', 'created_at']

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None

    def get_download_url(self, obj):
        return f"/api/candidate-attachments/{obj.attachment_id}/download/"

    def get_preview_url(self, obj):
        return f"/api/candidate-attachments/{obj.attachment_id}/preview/"

    def get_file_type_display(self, obj):
        if obj.is_pdf():
            return "PDF Document"
        elif obj.is_image():
            return "Image"
        elif obj.is_document():
            return "Document"
        elif obj.is_spreadsheet():
            return "Spreadsheet"
        else:
            return "File"


class InterviewConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewConversation
        fields = '__all__'

class InterviewSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    recruiter_name = serializers.CharField(source='recruiter.get_full_name', read_only=True)
    recruiter_email = serializers.CharField(source='recruiter.email', read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    end_time = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Interview
        fields = [
            'interview_id',
            'candidate', 'recruiter',
            'candidate_name', 'candidate_email',
            'recruiter_name', 'recruiter_email',
            'title', 'description',
            'scheduled_at', 'duration', 'end_time',
            'interview_link', 'required_preparation',
            'status', 'google_event_id', 'google_calendar_link', 'send_calendar_invite',
            'is_upcoming', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'candidate_name', 'candidate_email',
            'recruiter_name', 'recruiter_email',
            'end_time', 'is_upcoming', 'google_event_id',
            'google_calendar_link', 'created_at', 'updated_at',
            'completed_at'
        ]
    
    def validate(self, data):
        if self.instance is None and 'scheduled_at' in data:
            from django.utils import timezone
            if data['scheduled_at'] <= timezone.now():
                raise serializers.ValidationError({
                    'scheduled_at': 'Interview must be scheduled for a future time.'
                })
        return data
    
    def validate_scheduled_at(self, value):
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("Interview must be scheduled for a future time.")
        return value
    
    def validate_duration(self, value):
        if value < 15:
            raise serializers.ValidationError("Interview duration must be at least 15 minutes.")
        if value > 480:
            raise serializers.ValidationError("Interview duration cannot exceed 8 hours.")
        return value
    
class InterviewCreateSerializer(InterviewSerializer):
    class Meta(InterviewSerializer.Meta):
        read_only_fields = InterviewSerializer.Meta.read_only_fields + [
            'status', 'result'  
        ]
    
    def validate(self, data):
        data = super().validate(data)
        if self.instance is None and 'candidate' not in data:
            raise serializers.ValidationError({
                'candidate': 'This field is required when creating an interview.'
            })
        if self.instance is None and 'recruiter' not in data:
            raise serializers.ValidationError({
                'recruiter': 'This field is required when creating an interview.'
            })
        if self.instance is None:
            data['status'] = 'draft'
        return data
    
    def create(self, validated_data):
        if 'recruiter' not in validated_data:
            validated_data['recruiter'] = self.context['request'].user
        return super().create(validated_data)

class InterviewUpdateSerializer(InterviewSerializer):
    class Meta(InterviewSerializer.Meta):
        read_only_fields = InterviewSerializer.Meta.read_only_fields + [
            'candidate',  'recruiter'
        ]
    
    def validate(self, data):
        data = super().validate(data)
        if self.instance and self.instance.status != 'draft':
            restricted_fields = ['candidate', 'recruiter']
            for field in restricted_fields:
                if field in data and getattr(self.instance, field) != data[field]:
                    raise serializers.ValidationError({
                        field: f'Cannot change {field} after interview is scheduled.'
                    })
        return data

class InterviewListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    job_title = serializers.CharField(source='job.job_title', read_only=True)
    company_name = serializers.CharField(source='company.company_name', read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Interview
        fields = [
            'candidate_id', 'candidate_name', 'job_title', 'company_name', 'scheduled_at',
            'status', 'is_upcoming', 'created_at'
        ]

class InterviewCalendarSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True)
    start = serializers.DateTimeField(source='scheduled_at', read_only=True)
    end = serializers.SerializerMethodField(read_only=True)
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    job_title = serializers.CharField(source='job.job_title', read_only=True)
    interview_type = serializers.CharField(read_only=True)
    
    class Meta:
        model = Interview
        fields = [
            'interview_id', 'title', 'start', 'end', 'candidate_name', 
            'job_title', 'interview_type', 'status', 'interview_link'
        ]
    
    def get_end(self, obj):
        return obj.end_time

class InterviewCandidateChoiceSerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(source='candidate_id')
    label = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = ['value', 'label']
    
    def get_label(self, obj):
        return f"{obj.name} - {obj.email} - {obj.job.job_title}"

class InterviewJobChoiceSerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(source='job_id')
    label = serializers.CharField(source='job_title')
    
    class Meta:
        model = Job
        fields = ['value', 'label']

class InterviewCompanyChoiceSerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(source='company_id')
    label = serializers.CharField(source='company_name')
    
    class Meta:
        model = Company
        fields = ['value', 'label']

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
            'company': {'required': True},
            'expired_at': {'required': False},
            'generated_job_summary': {'read_only': True},
        }

class CandidateSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.job_title', read_only=True)
    company_name = serializers.CharField(source='job.company.company_name', read_only=True)
    attachments = CandidateAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Candidate
        fields = [
            'candidate_id', 'job', 'job_title', 'company_name', 'odoo_candidate_id',
            'name', 'email', 'phone', 'generated_skill_summary', 'state',
            'partner_id', 'date_open', 'date_last_stage_update',
            'created_at', 'updated_at', 'attachments'
        ]
        read_only_fields = ['candidate_id', 'created_at', 'updated_at']

class RecruiterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    class Meta:
        model = Recruiter
        fields = ['id', 'first_name', 'last_name', 'email', 'password', 'image', 'created_at', 'updated_at']
        extra_kwargs = {'password': {'write_only': True, 'required': False}}
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Recruiter(**validated_data)
        user.set_password(password)
        user.save()
        return user
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs

class OdooCredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OdooCredentials
        fields = ['credentials_id', 'odoo_user_id', 'email_address', 'db_name', 'db_url', 'created_at', 'updated_at']
        read_only_fields = ['credentials_id', 'created_at', 'updated_at']

    def validate(self, attrs):
        return attrs
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.pop('api_key', None)
        return representation

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