from rest_framework import serializers
from .models import AIReport

class AIReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIReport
        fields = [
            'report_id',
            'conversation_id',
            'skill_match_score',
            'final_match_score',
            'strengths',
            'weaknesses',
            'overall_recommendation',
            'skills_breakdown',
            'initial_analysis',
            'performance_analysis',
            'created_at',
            'updated_at'
        ]
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