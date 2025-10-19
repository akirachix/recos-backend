
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from datetime import timedelta
from users.models import OdooCredentials
from users.services.odoo_service import OdooService
from companies.models import Company
from job.models import Job
from job.services.ai_service import generate_job_summary

class JobSyncService:
    @staticmethod
    def _parse_odoo_date(odoo_date_string):
        """Parse Odoo date string to a timezone-aware Python datetime."""
        if not odoo_date_string:
            return None
        try:
            naive_dt = parse_datetime(odoo_date_string)
            return timezone.make_aware(naive_dt)
        except (ValueError, TypeError):
            return None  

    @staticmethod
    def sync_jobs_for_company(company):
        try:
            recruiter = company.recruiter
            odoo_creds = company.odoo_credentials
            if not odoo_creds:
                raise ValueError("No Odoo credentials found for this recruiter")
                
            odoo_service = OdooService(
                db_url=odoo_creds.db_url,
                db_name=odoo_creds.db_name,
                email=odoo_creds.email_address,
                api_key=odoo_creds.get_api_key()
            )
            
            if not odoo_service.authenticate():
                raise Exception("Failed to authenticate with Odoo")
        
            if not company.odoo_company_id:
                return []
                
            odoo_jobs = odoo_service.get_jobs(user_id=odoo_creds.odoo_user_id, company_id=company.odoo_company_id)
            
            synced_jobs = []
            
            for odoo_job in odoo_jobs:
                job_description = odoo_job.get('description', '')
                if job_description is False or job_description == 'False':
                    job_description = ''
                
                job, created = Job.objects.update_or_create(
                    company=company,
                    odoo_job_id=odoo_job['id'], 
                    defaults={
                        'job_title': odoo_job['name'],
                        'job_description': job_description,
                        'generated_job_summary': generate_job_summary(job_description) if job_description else 'No job description available for summary generation.',
                        'state': odoo_job.get('state', 'open'),
                        'expired_at': timezone.now() + timedelta(days=365),
                        'posted_at': JobSyncService._parse_odoo_date(odoo_job.get('create_date'))
                    }
                )
                
                action = "Created" if created else "Updated"
                synced_jobs.append(job)
            
            return synced_jobs
        except Exception as e:
            raise

    @staticmethod
    def sync_jobs_for_user(recruiter):
        try:
            odoo_creds = OdooCredentials.objects.filter(recruiter=recruiter).last()
            if not odoo_creds:
                raise ValueError("No Odoo credentials found for this recruiter")
                
            odoo_service = OdooService(
                db_url=odoo_creds.db_url,
                db_name=odoo_creds.db_name,
                email=odoo_creds.email_address,
                api_key=odoo_creds.get_api_key()
            )
            
            if not odoo_service.authenticate():
                raise Exception("Failed to authenticate with Odoo")
            
            odoo_jobs = odoo_service.get_jobs_by_user(user_id=odoo_creds.odoo_user_id)
            synced_jobs = []
            
            companies = Company.objects.filter(recruiter=recruiter)
            company_map = {company.odoo_company_id: company for company in companies if company.odoo_company_id}
            
            for odoo_job in odoo_jobs:
                odoo_company_id = None
                if odoo_job.get('company_id') and isinstance(odoo_job['company_id'], list):
                    odoo_company_id = odoo_job['company_id'][0]
                
                if not odoo_company_id or odoo_company_id not in company_map:
                    continue
                
                company = company_map[odoo_company_id]
                job, created = Job.objects.update_or_create(
                    company=company,
                    odoo_job_id=odoo_job['id'], 
                    defaults={
                        'job_title': odoo_job['name'],
                        'job_description': odoo_job.get('description', ''),
                        'generated_job_summary': generate_job_summary(odoo_job.get('description', '')),
                        'state': odoo_job.get('state', 'open'),
                        'expired_at': timezone.now() + timedelta(days=365),
                        'posted_at': JobSyncService._parse_odoo_date(odoo_job.get('create_date'))
                    }
                )
                
                synced_jobs.append(job)
            
            return synced_jobs
        except Exception as e:
            raise