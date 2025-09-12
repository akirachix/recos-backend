from django.db import models
from candidate.models import Candidate
from users.models import Recruiter
from django.core.validators import MinValueValidator, MaxValueValidator

class Interview(models.Model):  
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]
    
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='interviews')
    recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE, related_name='interviews')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    scheduled_at = models.DateTimeField()
    duration = models.IntegerField(
        default=60, 
        help_text="Duration in minutes",
        validators=[MinValueValidator(15), MaxValueValidator(480)]  # 15min to 8hrs
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    interview_link = models.URLField(blank=True, null=True)
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    google_calendar_link = models.URLField(blank=True, null=True)
    send_calendar_invite = models.BooleanField(default=True)
    required_preparation = models.TextField(blank=True, null=True, help_text="Preparation materials for candidate")    
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
        from django.utils import timezone
        return self.status == 'scheduled' and self.scheduled_at > timezone.now()
    
    @property
    def end_time(self):
        from datetime import timedelta
        return self.scheduled_at + timedelta(minutes=self.duration)
    
    def save(self, *args, **kwargs):
        # Auto-update status based on timing
        from django.utils import timezone
        now = timezone.now()
        
        if self.status == 'scheduled' and self.scheduled_at <= now:
            self.status = 'in_progress'
        
        if self.status == 'in_progress' and self.end_time <= now:
            self.status = 'completed'
            if not self.completed_at:
                self.completed_at = now
        
        super().save(*args, **kwargs)