from rest_framework import serializers
from interviewConversation.models import InterviewConversation

class InterviewConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewConversation
        fields = '__all__'
