from django.db import models
from companies.models import Company

class Job(models.Model):
    JOB_STATES = [
        ('open', 'Open'),
        ('recruit', 'Recruitment in Progress'),
        ('pause', 'Paused'),
        ('close', 'Closed'),
        ('cancel', 'Cancelled'),
    ]
    
    job_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    job_title = models.CharField(max_length=100)
    job_description = models.TextField()
    generated_job_summary = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=50, choices=JOB_STATES, default='open') 
    posted_at = models.DateTimeField()
    expired_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.job_title   