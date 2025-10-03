from django.db import models
from candidate.models import Candidate
from users.models import Recruiter
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta

class Interview(models.Model):  
    STATUS_SCHEDULED = 'scheduled'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELED = 'canceled'

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELED, 'Canceled'),
    ]

    interview_id = models.AutoField(primary_key=True)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='interviews')
    recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE, related_name='interviews')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    scheduled_at = models.DateTimeField()
    duration = models.PositiveIntegerField(
        default=60, 
        help_text="Duration in minutes",
        validators=[MinValueValidator(15), MaxValueValidator(480)] 
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED
    )
    interview_link = models.URLField(blank=True, null=True)
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    google_calendar_link = models.URLField(blank=True, null=True)
    send_calendar_invite = models.BooleanField(default=True)
    required_preparation = models.TextField(
        blank=True, null=True, help_text="Preparation materials for candidate"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['candidate', 'scheduled_at']),
            models.Index(fields=['recruiter', 'scheduled_at']),
            models.Index(fields=['status', 'scheduled_at']),
        ]
    
    def __str__(self):
        return f"{self.candidate.name} - {self.title} - {self.get_status_display()}"
    
    @property
    def is_upcoming(self):
        return self.status == self.STATUS_SCHEDULED and self.scheduled_at > timezone.now()
    
    @property
    def end_time(self):
        return self.scheduled_at + timedelta(minutes=self.duration)
    
    def save(self, *args, **kwargs):
        now = timezone.now()
        if self.status == self.STATUS_SCHEDULED and self.scheduled_at <= now:
            self.status = self.STATUS_IN_PROGRESS
        if self.status == self.STATUS_IN_PROGRESS and self.end_time <= now:
            self.status = self.STATUS_COMPLETED
            if not self.completed_at:
                self.completed_at = now
        super().save(*args, **kwargs)