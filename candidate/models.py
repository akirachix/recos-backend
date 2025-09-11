from django.db import models
from job.models import Job

class Candidate(models.Model):
    candidate_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    job= models.ForeignKey(Job, on_delete=models.CASCADE)
    generated_skill_summary = models.TextField(null=True, blank=True)
    state=models.CharField(max_length=50, default='applied')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
