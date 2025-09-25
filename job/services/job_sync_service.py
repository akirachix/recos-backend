from users.models import OdooCredentials
from users.services.odoo_service import OdooService
from companies.models import Company
from job.models import Job
from django.utils import timezone
from datetime import timedelta

class JobSyncService:
    @staticmethod
    def sync_jobs_for_company(company):
        try:
            recruiter = company.recruiter
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
            
            odoo_jobs = odoo_service.get_jobs(user_id=odoo_creds.odoo_user_id)
            synced_jobs = []
            
            for odoo_job in odoo_jobs:
               
                job_company_name = None
                
                if odoo_job.get('company_id') and isinstance(odoo_job['company_id'], list):
                    job_company_name = odoo_job['company_id'][1]
                
                if job_company_name != company.company_name:
                    continue
                
                job, created = Job.objects.update_or_create(
                    company=company,
                    job_title=odoo_job['name'],
                    defaults={
                        'job_description': odoo_job.get('description', ''),
                        'state': odoo_job.get('state', 'open'),
                        'expired_at': timezone.now() + timedelta(days=365),
                        'posted_at': odoo_job.get('create_date', timezone.now())
                    }
                )
                synced_jobs.append(job)
            
            return synced_jobs
        except Exception as e:
            print(f"Error syncing jobs for company {company.company_name}: {str(e)}")
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
            
            odoo_jobs = odoo_service.get_jobs(user_id=odoo_creds.odoo_user_id)
            synced_jobs = []
            
            companies = Company.objects.filter(recruiter=recruiter)
            
            company_map = {}
            for company in companies:
                if company.company_name not in company_map:
                    company_map[company.company_name] = company
            
            for odoo_job in odoo_jobs:
                job_company_name = None
                
                if odoo_job.get('company_id') and isinstance(odoo_job['company_id'], list):
                    job_company_name = odoo_job['company_id'][1]
                
                if not job_company_name or job_company_name not in company_map:
                    continue
                
                company = company_map[job_company_name]
                
                job, created = Job.objects.update_or_create(
                    company=company,
                    job_title=odoo_job['name'],
                    defaults={
                        'job_description': odoo_job.get('description', ''),
                        'state': odoo_job.get('state', 'open'),
                        'expired_at': timezone.now() + timedelta(days=365),
                        'posted_at': odoo_job.get('create_date', timezone.now())
                    }
                )
                synced_jobs.append(job)
            
            return synced_jobs
        except Exception as e:
            print(f"Error syncing jobs for user {recruiter.email}: {str(e)}")
            raise