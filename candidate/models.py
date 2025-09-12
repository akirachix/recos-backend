from django.db import models
from job.models import Job
import os

class Candidate(models.Model):
    CANDIDATE_STATES = [
        ('applied', 'Applied'),
        ('qualified', 'Qualified'),
        ('interview', 'Interview'),
        ('offer', 'Offer'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    ]
    
    candidate_id = models.AutoField(primary_key=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='candidates')
    odoo_candidate_id = models.IntegerField(null=True, blank=True)  
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)  
    generated_skill_summary = models.TextField(null=True, blank=True)
    state = models.CharField(max_length=50, choices=CANDIDATE_STATES, default='applied')
    partner_id = models.IntegerField(null=True, blank=True)  
    date_open = models.DateTimeField(null=True, blank=True)  
    date_last_stage_update = models.DateTimeField(null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('job', 'odoo_candidate_id') 
    
    def __str__(self):
        return self.name
    

class CandidateAttachment(models.Model):
    attachment_id = models.AutoField(primary_key=True)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='attachments')
    odoo_attachment_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    file = models.FileField(upload_to='candidate_attachments/%Y/%m/%d/')
    file_type = models.CharField(max_length=100)
    file_size = models.IntegerField(default=0)
    sync_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='completed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.candidate.name}"
    
    def get_download_filename(self):
        """Get filename for download (preserve original extension)"""
        if self.original_filename:
            return self.original_filename
        # Fallback: use the stored file name or generate one
        if self.file and hasattr(self.file, 'name'):
            return os.path.basename(self.file.name)
        return f"{self.name or 'attachment'}_{self.attachment_id}"
    
    def get_file_extension(self):
        """Get file extension from filename"""
        if self.file and self.file.name:
            return os.path.splitext(self.file.name)[1].lower()
        return ''
    
    def is_pdf(self):
        return self.get_file_extension() == '.pdf'
    
    def is_image(self):
        return self.get_file_extension() in ['.jpg', '.jpeg', '.png', '.gif']
    
    def is_document(self):
        return self.get_file_extension() in ['.doc', '.docx', '.pdf', '.txt']
    
    class Meta:
        ordering = ['-created_at']