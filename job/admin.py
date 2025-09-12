from django.contrib import admin
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        'job_title',
        'company',
        'recruiter',
        'odoo_job_id',
        'state',
        'is_active',
        'posted_at',
        'expired_at',
        'created_at',
        'updated_at',
    ]
    search_fields = [
        'job_title',
        'company__company_name',
        'recruiter__email',
        'odoo_job_id',
    ]
    list_filter = [
        'state',
        'is_active',
        'company',
        'recruiter',
    ]