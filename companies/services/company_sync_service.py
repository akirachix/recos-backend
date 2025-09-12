from users.models import OdooCredentials
from users.services.odoo_service import OdooService
from companies.models import Company


class CompanySyncService:
    @staticmethod
    def sync_recruiter_companies(recruiter, sync_jobs=False):
     
        try:
            odoo_creds = OdooCredentials.objects.filter(
                recruiter=recruiter
            ).order_by('-created_at').first()
            
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
                        'is_active': True
                    }
                )
                synced_companies.append(company)
                
                if sync_jobs:
                    CompanySyncService._sync_jobs_for_company(company, odoo_service)
            
            CompanySyncService._deactivate_removed_companies(
                recruiter, 
                [company['id'] for company in odoo_companies]
            )
            
            return synced_companies
            
        except Exception as e:
            raise
    
    @staticmethod
    def _sync_jobs_for_company(company, odoo_service):
        """Helper method to sync jobs for a company"""
        try:
            from job.services.job_sync_service import JobSyncService
            JobSyncService.sync_jobs_for_company(company, odoo_service)
        except ImportError:
            return "JobSyncService not available - skipping job sync"
        except Exception as e:
            return f"Error syncing jobs for company {company.company_name}: {str(e)}"
    
    @staticmethod
    def _deactivate_removed_companies(recruiter, active_odoo_company_ids):
        """
        Deactivate companies that are no longer in Odoo
        """
        Company.objects.filter(
            recruiter=recruiter,
            is_active=True
        ).exclude(
            odoo_company_id__in=active_odoo_company_ids
        ).update(is_active=False)

    
