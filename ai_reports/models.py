from django.db import models
from django.utils import timezone

class AIReport(models.Model):
    report_id = models.AutoField(primary_key=True)
    conversation_id = models.IntegerField()
    skill_match_score = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    final_match_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    strengths = models.TextField(null=True, blank=True)
    weaknesses = models.TextField(null=True, blank=True)
    overall_recommendation = models.TextField(null=True, blank=True)
    skills_breakdown = models.JSONField(default=dict, blank=True, null=True)
    initial_analysis = models.JSONField(default=dict, blank=True, null=True)
    performance_analysis = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"AI Report #{self.report_id} for Conversation {self.conversation_id}"