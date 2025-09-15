from users.models import OdooCredentials
from users.services.odoo_service import OdooService
from django.utils.dateparse import parse_datetime
import base64
from candidate.models import Candidate, CandidateAttachment
from django.core.files.base import ContentFile
import mimetypes
import os
from job.models import Job 
from datetime import timezone, timedelta

class CandidateSyncService:
    @staticmethod
    def sync_candidates_for_job(job, odoo_service=None):
        """Sync candidates from Odoo for a given job including attachments"""
        try:            
            if not odoo_service:
                recruiter = job.company.recruiter
                
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
            
            odoo_candidates = odoo_service.get_candidates(job_id=job.job_id)

            synced_candidates = []
            for odoo_candidate in odoo_candidates:
                try:
                    candidate = CandidateSyncService._process_single_candidate(odoo_candidate, job)
                    
                    CandidateSyncService.sync_attachments_for_candidate(candidate, odoo_service)
                    
                    synced_candidates.append(candidate)
                except Exception as e:
                    print(f"Error processing candidate {odoo_candidate.get('id')}: {str(e)}")
                    continue
            
            return synced_candidates
            
        except Exception as e:
            print(f"Error syncing candidates for job {job.job_title}: {str(e)}")
            raise

    @staticmethod
    def _process_single_candidate(odoo_candidate, job):
        """Process a single candidate from Odoo"""
        
        candidate_name = odoo_candidate.get('partner_name', 'Unknown Candidate')
        
        stage_data = odoo_candidate.get('stage_id', [False, 'Applied'])
        if isinstance(stage_data, list) and len(stage_data) > 1:
            stage_name = stage_data[1]
        else:
            stage_name = 'Applied'
        
        state = CandidateSyncService._map_odoo_stage(stage_name)
        
        candidate_data = {
            'name': candidate_name,  
            'email': odoo_candidate.get('email_from', ''),
            'phone': odoo_candidate.get('phone', '') or odoo_candidate.get('partner_phone', ''),
            'state': state,
        }
        
        partner_id_data = odoo_candidate.get('partner_id', [False])
        if isinstance(partner_id_data, list) and len(partner_id_data) > 0:
            candidate_data['partner_id'] = partner_id_data[0]
        
        candidate_data['date_open'] = CandidateSyncService._parse_odoo_date(
            odoo_candidate.get('date_open')
        )
        
        candidate_data['date_last_stage_update'] = CandidateSyncService._parse_odoo_date(
            odoo_candidate.get('date_last_stage_update')
        )
        
        candidate, created = Candidate.objects.update_or_create(
            job=job,
            odoo_candidate_id=odoo_candidate['id'],
            defaults=candidate_data
        )
        
        return candidate

    @staticmethod
    def sync_candidates_for_company(company, odoo_service=None):
        """Sync all candidates for a company (all jobs)"""
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
            
            company_jobs = Job.objects.filter(company=company)
            job_titles = [job.job_title for job in company_jobs]
            
            odoo_candidates = odoo_service.get_candidates(company_id=company.odoo_company_id)
            
            synced_count = 0
            for odoo_candidate in odoo_candidates:
                try:
                    job_id_data = odoo_candidate.get('job_id', [False, 'Unknown Job'])
                    if isinstance(job_id_data, list) and len(job_id_data) > 1:
                        job_title = job_id_data[1]
                    else:
                        job_title = 'Unknown Job'
                    
                    matching_job = None
                    for job in company_jobs:
                        if job.job_title == job_title:
                            matching_job = job
                            break
                    
                    if not matching_job:
                        for job in company_jobs:
                            if job_title.lower() in job.job_title.lower() or job.job_title.lower() in job_title.lower():
                                matching_job = job
                                break
                    
                    if not matching_job:
                        matching_job, created = Job.objects.get_or_create(
                            company=company,
                            job_title=job_title,
                            defaults={
                                'job_description': f"Auto-created for candidate sync: {job_title}",
                                'state': 'open',
                                'expired_at': timezone.now() + timedelta(days=365)
                            }
                        )
                        company_jobs = Job.objects.filter(company=company)  
                    
                    candidate = CandidateSyncService._process_single_candidate(odoo_candidate, matching_job)
                    CandidateSyncService.sync_attachments_for_candidate(candidate, odoo_service)
                    
                    synced_count += 1
                    
                except Exception as e:
                    print(f"Error processing candidate {odoo_candidate.get('id')}: {str(e)}")
                    continue
            
            return synced_count
            
        except Exception as e:
            print(f"Error syncing candidates for company {company.company_name}: {str(e)}")
            raise

    @staticmethod
    def sync_all_candidates_for_recruiter(recruiter):
        """Sync candidates for all companies of a recruiter"""
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
            
            from companies.models import Company
            companies = Company.objects.filter(recruiter=recruiter)
            
            total_synced = 0
            for company in companies:
                try:
                    synced_count = CandidateSyncService.sync_candidates_for_company(company, odoo_service)
                    total_synced += synced_count
                    print(f"Synced {synced_count} candidates for company {company.company_name}")
                except Exception as e:
                    print(f"Error syncing candidates for company {company.company_name}: {str(e)}")
                    continue
            
            return total_synced
            
        except Exception as e:
            print(f"Error syncing all candidates for recruiter {recruiter.email}: {str(e)}")
            raise
    
    @staticmethod
    def _map_odoo_stage(odoo_stage_name):
        """Map Odoo stage names to our state choices"""
        stage_mapping = {
            'Applied': 'applied',
            'Qualified': 'qualified',
            'First Interview': 'interview',
            'Second Interview': 'interview',
            'Contract Proposal': 'offer',
            'Contract Signed': 'hired',
            'Refused': 'rejected',
            'Hired': 'hired',
        }
        return stage_mapping.get(odoo_stage_name, 'applied')
    
    @staticmethod
    def _parse_odoo_date(odoo_date_string):
        """Parse Odoo date string to Python datetime"""
        if not odoo_date_string:
            return None
        try:
            return parse_datetime(odoo_date_string)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def sync_attachments_for_candidate(candidate, odoo_service):
        """Sync attachments for a single candidate"""
        try:
            attachments = odoo_service.get_attachments(
                res_model='hr.applicant',
                res_id=candidate.odoo_candidate_id
            )
            
            
            for attachment_data in attachments:
                try:
                    CandidateSyncService._process_single_attachment(candidate, attachment_data, odoo_service)
                except Exception as e:
                    continue
            
        except Exception as e:
            return f"Error syncing attachments for candidate {candidate.name}: {str(e)}"

    @staticmethod
    def _process_single_attachment(candidate, attachment_data, odoo_service):
        """Process a single attachment with base64 decoding"""
        attachment_id = attachment_data['id']
        attachment_name = attachment_data.get('name', f'attachment_{attachment_id}')
        attachment_type = attachment_data.get('mimetype', 'application/octet-stream')
        
        if CandidateAttachment.objects.filter(
            candidate=candidate, 
            odoo_attachment_id=attachment_id
        ).exists():
            return
        
        try:
            attachment_detail = odoo_service.get_attachment_content(attachment_id)
            
            if attachment_detail and 'datas' in attachment_detail:
                base64_data = attachment_detail['datas']
                file_content = base64.b64decode(base64_data)
                
                original_filename = attachment_detail.get('datas_fname', attachment_detail.get('name', f'attachment_{attachment_id}'))
                
                file_extension = CandidateSyncService._get_file_extension(
                    attachment_detail.get('mimetype'), 
                    original_filename
                )
                
                file_name = CandidateSyncService._generate_filename(
                    attachment_name, 
                    file_extension, 
                    attachment_id
                )
                
                attachment = CandidateAttachment(
                    candidate=candidate,
                    odoo_attachment_id=attachment_id,
                    name=attachment_name,
                    file_type=attachment_type,
                    file_size=len(file_content),
                    original_filename=original_filename
                )
                
                attachment.file.save(file_name, ContentFile(file_content))
                attachment.save()
                                
            else:

                attachment = CandidateAttachment(
                    candidate=candidate,
                    odoo_attachment_id=attachment_id,
                    name=attachment_name,
                    file_type=attachment_type,
                    file_size=0,
                    sync_status='failed',
                    original_filename=attachment_name  
                )
                attachment.save()
                
        except Exception as e:
            attachment = CandidateAttachment(
                candidate=candidate,
                odoo_attachment_id=attachment_id,
                name=attachment_name,
                file_type=attachment_type,
                file_size=0,
                sync_status='failed',
                original_filename=attachment_name 
            )
            attachment.save()

    @staticmethod
    def _get_file_extension(mimetype, original_filename):
        """Get appropriate file extension from mimetype or filename"""
        import mimetypes
        if original_filename:
            _, ext = os.path.splitext(original_filename)
            if ext:
                return ext.lower()
        
        if mimetype:
            ext = mimetypes.guess_extension(mimetype)
            if ext:
                return ext.lower()
        
        return '.bin'
    
    @staticmethod
    def _generate_filename(attachment_name, file_extension, attachment_id):
        """Generate a safe filename for storage"""
        import re
        clean_name = re.sub(r'[^\w\s-]', '', attachment_name)
        clean_name = re.sub(r'[-\s]+', '-', clean_name)
        
        if len(clean_name) > 50:
            clean_name = clean_name[:50]
        
        return f"candidate_attachment_{attachment_id}_{clean_name}{file_extension}"
   