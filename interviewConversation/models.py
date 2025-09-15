from django.db import models
from interview.models import Interview

class InterviewConversation(models.Model):
    conversation_id = models.AutoField(primary_key=True)
    interview = models.ForeignKey(
        Interview,
        to_field='interview_id',     
        on_delete=models.CASCADE,
        related_name='conversations'
    )
    question_text = models.TextField()
    expected_answer = models.TextField(null=True, blank=True)
    candidate_answer = models.TextField(null=True, blank=True)
    transcript_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation {self.conversation_id} for Interview {self.interview_id}"