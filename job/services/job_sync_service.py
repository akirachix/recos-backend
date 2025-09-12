from job.models import Job
from users.models import OdooCredentials
from users.services.odoo_service import OdooService

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

            # You would need this method in your OdooService
            odoo_jobs = odoo_service.get_company_jobs(company.odoo_company_id)

            synced_jobs = []
            for odoo_job in odoo_jobs:
                job, created = Job.objects.update_or_create(
                    recruiter=recruiter,
                    company=company,
                    odoo_job_id=odoo_job['id'],
                    defaults={
                        'job_title': odoo_job['name'],
                        'job_description': odoo_job.get('description', ''),
                        'state': odoo_job.get('state', 'open'),
                        'is_active': odoo_job.get('is_active', True),
                        'expired_at': odoo_job.get('expired_at', None),
                        'generated_job_summary': odoo_job.get('summary', ''),
                    }
                )
                synced_jobs.append(job)
            return synced_jobs

        except Exception as e:
            print(f"Error syncing jobs: {str(e)}")
            raise