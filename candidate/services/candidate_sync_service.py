from users.models import OdooCredentials
from users.services.odoo_service import OdooService
from companies.models import Company
from job.models import Job
from candidate.models import  Candidate
class CandidateSyncService:
    @staticmethod
    def sync_candidates_for_job(job):
        """Sync candidates from Odoo for a given job"""
        try:
            recruiter = job.recruiter
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
            # Get candidates for this job
            odoo_candidates = odoo_service.get_candidates(job_id=job.odoo_job_id)
            synced_candidates = []
            for odoo_candidate in odoo_candidates:
                # Extract stage name from stage_id if available
                stage = odoo_candidate.get('stage_id', [False, 'applied'])
                if isinstance(stage, list) and len(stage) > 1:
                    state = stage[1]
                else:
                    state = 'applied'
                candidate, created = Candidate.objects.update_or_create(
                    job=job,
                    company=job.company,
                    recruiter=recruiter,
                    odoo_candidate_id=odoo_candidate['id'],
                    defaults={
                        'name': odoo_candidate.get('partner_name') or odoo_candidate.get('name', ''),
                        'email': odoo_candidate.get('email_from', ''),
                        'phone': odoo_candidate.get('phone', ''),
                        'state': state,
                        'partner_id': odoo_candidate.get('partner_id', [False])[0] if odoo_candidate.get('partner_id') else None,
                        'date_open': odoo_candidate.get('date_open'),
                        'date_last_stage_update': odoo_candidate.get('date_last_stage_update')
                    }
                )
                synced_candidates.append(candidate)
            return synced_candidates
        except Exception as e:
            print(f"Error syncing candidates for job {job.job_title}: {str(e)}")
            raise