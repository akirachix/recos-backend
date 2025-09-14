from users.models import OdooCredentials
from users.services.odoo_service import OdooService
from job.models import Job
class JobSyncService:
    @staticmethod
    def sync_jobs_for_company(company, odoo_service=None):
        try:
            if not odoo_service:
                recruiter = company.recruiter
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
            
            odoo_jobs = odoo_service.get_jobs(company_id=company.odoo_company_id)
            
            synced_jobs = []
            for odoo_job in odoo_jobs:
                job, created = Job.objects.update_or_create(
                    company=company,
                    odoo_job_id=odoo_job['id'],  
                    defaults={
                        'job_title': odoo_job['name'],
                        'job_description': odoo_job.get('description', ''),  
                        'state': JobSyncService._map_odoo_state(odoo_job.get('state', 'open')),
                        'expired_at': JobSyncService._parse_odoo_date(
                            odoo_job.get('expired_at')
                        ) if odoo_job.get('expired_at') else None
                    }
                )
                synced_jobs.append(job)

            try:
                from candidate.services.candidate_sync_service import CandidateSyncService
                for job in synced_jobs:
                    try:
                        CandidateSyncService.sync_candidates_for_job(job, odoo_service)
                    except Exception as e:
                        return f"Error syncing candidates for job {job.job_title}: {str(e)}"
            except ImportError:
                return "CandidateSyncService not available - skipping candidate sync"
        
            JobSyncService._deactivate_removed_jobs(company, odoo_jobs)
            
            return synced_jobs
        
        
            
        except Exception as e:
            raise
     
    
    @staticmethod
    def _map_odoo_state(odoo_state):
        state_mapping = {
            'open': 'open',
            'recruit': 'recruit', 
            'pause': 'pause',
            'close': 'close',
            'cancel': 'cancel',
        }
        return state_mapping.get(odoo_state, 'open')
    
    @staticmethod
    def _parse_odoo_date(odoo_date_string):
        from django.utils.dateparse import parse_datetime
        return parse_datetime(odoo_date_string)
    
    @staticmethod
    def _deactivate_removed_jobs(company, odoo_jobs):
        active_odoo_job_ids = [job['id'] for job in odoo_jobs]
        
        Job.objects.filter(
            company=company,
            odoo_job_id__isnull=False
        ).exclude(
            odoo_job_id__in=active_odoo_job_ids
        ).update(state='close')