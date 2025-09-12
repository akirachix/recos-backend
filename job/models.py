from django.db import models
from users.models import Recruiter
from companies.models import Company

class Job(models.Model):
    job_id = models.AutoField(primary_key=True)
    odoo_job_id = models.IntegerField(null=True, blank=True)
    job_title = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE, related_name='jobs')
    job_description = models.TextField()
    generated_job_summary = models.TextField(null=True, blank=True)
    state = models.CharField(max_length=50, default='open')
    is_active = models.BooleanField(default=True)
    posted_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('recruiter', 'job_title', 'company')
    
    def __str__(self):
        return self.job_title