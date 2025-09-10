from django.db import models
# from job.models import Job
# from candidate.models import Candidate
# from recruiter.models import Recruiter

class Interview(models.Model):
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Canceled', 'Canceled'),
    ]
    # job = models.ForeignKey(Job, on_delete=models.CASCADE)
    # candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    # recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE)
    scheduled_at = models.DateTimeField()
    interview_link = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Interview: {self.pk} ({self.status})"