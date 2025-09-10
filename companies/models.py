from django.db import models
from users.models import Recruiter

class Company(models.Model):
    company_id = models.AutoField(primary_key=True)
    odoo_company_id = models.IntegerField(null=True, blank=True)
    company_name = models.CharField(max_length=100)
    recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE, related_name='companies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('recruiter', 'company_name')
    
    def __str__(self):
        return self.company_name