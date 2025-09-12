from django.db import models
from companies.models import Company

class Job(models.Model):
    job_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    job_title = models.CharField(max_length=100)
    job_description = models.TextField()
    generated_job_summary = models.TextField()
    state = models.CharField(max_length=50, default='open')
    posted_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.job_title