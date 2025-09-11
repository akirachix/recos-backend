from users.models import OdooCredentials
from users.services.odoo_service import OdooService
from companies.models import Company
from job.models import Job
class JobSyncService:
    @staticmethod
    def sync_jobs_for_company(company):
        """Sync jobs from Odoo for a given company"""
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
            # Get jobs for this company
            odoo_jobs = odoo_service.get_jobs(company_id=company.odoo_company_id)
            synced_jobs = []
            for odoo_job in odoo_jobs:
                job, created = Job.objects.update_or_create(
                    company=company,
                    recruiter=recruiter,
                    odoo_job_id=odoo_job['id'],
                    defaults={
                        'job_title': odoo_job['name'],
                        'description': odoo_job.get('description', ''),
                        'state': odoo_job.get('state', 'open'),
                        'no_of_recruitment': odoo_job.get('no_of_recruitment', 1),
                        'no_of_hired_employee': odoo_job.get('no_of_hired_employee', 0),
                        'employee_id': odoo_job.get('employee_id', [False])[0] if odoo_job.get('employee_id') else None
                    }
                )
                synced_jobs.append(job)
            return synced_jobs
        except Exception as e:
            print(f"Error syncing jobs for company {company.company_name}: {str(e)}")
            raise