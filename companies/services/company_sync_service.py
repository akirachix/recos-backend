from users.models import OdooCredentials
from users.services.odoo_service import OdooService
from .models import Company
from .job_sync_services import JobSyncServices
class CompanySyncService:
    @staticmethod
    def sync_recruiter_companies(recruiter):
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
            
            odoo_companies = odoo_service.get_user_companies()
            
            synced_companies = []
            for odoo_company in odoo_companies:
                company, created = Company.objects.update_or_create(
                    recruiter=recruiter,
                    odoo_company_id=odoo_company['id'],
                    defaults={
                        'company_name': odoo_company['name'],
                        'country_id': odoo_company.get('country_id', [False])[0],
                        'is_active': True
                    }
                )
                synced_companies.append(company)
                if sync_jobs:
                    JobSyncServices.sync_jobs_for_company(company)
            
            return synced_companies
            
        except Exception as e:
            print(f"Error syncing companies: {str(e)}")
            raise