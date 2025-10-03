from django.db import models
from users.models import Recruiter, OdooCredentials
class Company(models.Model):
    company_id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=100)
    recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE, related_name='companies')
    odoo_company_id = models.IntegerField(null=True, blank=True) 
    odoo_credentials = models.ForeignKey(OdooCredentials, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['recruiter', 'company_name'], name='unique_recruiter_company_name')
        ]
    def __str__(self):
        return self.company_name