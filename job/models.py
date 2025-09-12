from django.db import models
from companies.models import Company
from django.contrib.auth import get_user_model

User = get_user_model()

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
    odoo_job_id = models.IntegerField(null=True, blank=True)  
    job_title = models.CharField(max_length=100)
    job_description = models.TextField()
    generated_job_summary = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=50, choices=JOB_STATES, default='open')  
    posted_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    recruiter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs_recruited')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('company', 'odoo_job_id')  
    
    def __str__(self):
        return self.job_title