from django.db import models

class Job(models.Model):
    job_id = models.AutoField(primary_key=True)
    job_title = models.CharField(max_length=100)
    job_description = models.TextField()
    generated_job_summary = models.TextField()
    posted_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.job_title
  