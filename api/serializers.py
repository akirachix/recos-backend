from rest_framework import serializers
from interview.models import Interview

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