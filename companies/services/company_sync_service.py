from users.models import OdooCredentials
from users.services.odoo_service import OdooService
from companies.models import Company
from job.services.job_sync_service import JobSyncService
class CompanySyncService:
    @staticmethod
    def sync_recruiter_companies(recruiter, sync_jobs=False):
        try:
            print(f"Syncing companies for recruiter: {recruiter.email}")
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
            print(f"Found {len(odoo_companies)} companies in Odoo for user {recruiter.email}")
            synced_companies = []
            existing_companies = Company.objects.filter(recruiter=recruiter)
            print(f"Found {existing_companies.count()} existing companies for this recruiter")
            for odoo_company in odoo_companies:
                print(f"Processing Odoo company: {odoo_company}")
                odoo_company_id = odoo_company['id']
                company_name = odoo_company['name']
                company = None
                if odoo_company_id:
                    company = existing_companies.filter(odoo_company_id=odoo_company_id).first()
                if company:
                    print(f"Found existing company by Odoo ID: {company.company_name} (ID: {company.company_id})")
                    if company.company_name != company_name:
                        company.company_name = company_name
                        company.save()
                        print(f"Updated company name to: {company_name}")
                else:
                    company = existing_companies.filter(company_name=company_name).first()
                    if company:
                        print(f"Found existing company by name: {company.company_name} (ID: {company.company_id})")
                        if not company.odoo_company_id:
                            company.odoo_company_id = odoo_company_id
                            company.save()
                            print(f"Updated Odoo ID to: {odoo_company_id}")
                    else:
                        print(f"Creating new company: {company_name}")
                        company = Company.objects.create(
                            odoo_company_id=odoo_company_id,
                            company_name=company_name,
                            recruiter=recruiter,
                            odoo_credentials=odoo_creds,
                            is_active=True
                        )
                        print(f"Created new company with ID: {company.company_id}")
                synced_companies.append(company)
                if sync_jobs:
                    from job.services.job_sync_service import JobSyncService
                    JobSyncService.sync_jobs_for_company(company)
            print(f"Successfully synced {len(synced_companies)} companies")
            return synced_companies
        except Exception as e:
            print(f"Error syncing companies: {str(e)}")
            raise