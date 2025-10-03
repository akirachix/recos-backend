from users.models import OdooCredentials
from users.services.odoo_service import OdooService
from companies.models import Company
from job.services.job_sync_service import JobSyncService
class CompanySyncService:
    @staticmethod
    def sync_recruiter_companies(recruiter, sync_jobs=False):
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
            existing_companies = Company.objects.filter(recruiter=recruiter)
            for odoo_company in odoo_companies:
                odoo_company_id = odoo_company['id']
                company_name = odoo_company['name']
                company = None
                if odoo_company_id:
                    company = existing_companies.filter(odoo_company_id=odoo_company_id).first()
                if company:
                    if company.company_name != company_name:
                        company.company_name = company_name
                        company.save()
                else:
                    company = existing_companies.filter(company_name=company_name).first()
                    if company:
                        if not company.odoo_company_id:
                            company.odoo_company_id = odoo_company_id
                            company.save()
                    else:
                        company = Company.objects.create(
                            odoo_company_id=odoo_company_id,
                            company_name=company_name,
                            recruiter=recruiter,
                            odoo_credentials=odoo_creds,
                            is_active=True
                        )
                synced_companies.append(company)
                if sync_jobs:
                    from job.services.job_sync_service import JobSyncService
                    JobSyncService.sync_jobs_for_company(company)
            return synced_companies
        except Exception as e:
            raise