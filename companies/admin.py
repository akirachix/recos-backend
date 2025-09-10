from django.contrib import admin
from .models import Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'recruiter', 'odoo_company_id', 'created_at', 'updated_at']
    search_fields = ['company_name', 'recruiter__email']