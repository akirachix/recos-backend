from django.contrib import admin
from .models import Recruiter, OdooCredentials

@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']

@admin.register(OdooCredentials)
class OdooCredentialsAdmin(admin.ModelAdmin):
    list_display = ['recruiter', 'db_name', 'email_address', 'created_at']
    search_fields = ['recruiter__username', 'recruiter__email', 'db_name', 'email_address']
    exclude = ['api_key']