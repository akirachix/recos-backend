import logging
from users.models import OdooCredentials
from users.services.odoo_service import OdooService
from django.utils.dateparse import parse_datetime
import base64
from candidate.models import Candidate, CandidateAttachment
from django.core.files.base import ContentFile
import mimetypes
import os
logger = logging.getLogger(__name__)

class CandidateSyncService:
    @staticmethod
    def sync_candidates_for_job(job, odoo_service=None):
        """Sync candidates from Odoo for a given job including attachments"""
        try:
            logger.info(f"Starting candidate sync for job: {job.job_title} (Odoo Job ID: {job.odoo_job_id})")
            
            # Use provided service or create new one
            if not odoo_service:
                # Get recruiter from job's company
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
            
            # Get candidates for this job from Odoo
            odoo_candidates = odoo_service.get_candidates(job_id=job.odoo_job_id)
            logger.info(f"Found {len(odoo_candidates)} candidates in Odoo for job {job.job_title}")
            
            synced_candidates = []
            for odoo_candidate in odoo_candidates:
                try:
                    candidate = CandidateSyncService._process_single_candidate(odoo_candidate, job)
                    
                    # Sync attachments for this candidate - THIS IS THE METHOD THAT SHOULD EXIST
                    CandidateSyncService.sync_attachments_for_candidate(candidate, odoo_service)
                    
                    synced_candidates.append(candidate)
                except Exception as e:
                    logger.error(f"Error processing candidate {odoo_candidate.get('id', 'unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Successfully synced {len(synced_candidates)} candidates with attachments for job {job.job_title}")
            return synced_candidates
            
        except Exception as e:
            logger.error(f"Error syncing candidates for job {job.job_title}: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _process_single_candidate(odoo_candidate, job):
        """Process a single candidate from Odoo"""
        
        # Use partner_name instead of name
        candidate_name = odoo_candidate.get('partner_name', 'Unknown Candidate')
        
        # Extract stage name from stage_id if available
        stage_data = odoo_candidate.get('stage_id', [False, 'Applied'])
        if isinstance(stage_data, list) and len(stage_data) > 1:
            stage_name = stage_data[1]
        else:
            stage_name = 'Applied'
        
        state = CandidateSyncService._map_odoo_stage(stage_name)
        
        # Build candidate data with correct field names
        candidate_data = {
            'name': candidate_name,  
            'email': odoo_candidate.get('email_from', ''),
            'state': state,
        }
        
        # Only add fields that exist in your model
        if hasattr(Candidate, 'phone'):
            candidate_data['phone'] = odoo_candidate.get('phone', '') or odoo_candidate.get('partner_phone', '')
        
        if hasattr(Candidate, 'partner_id'):
            partner_id_data = odoo_candidate.get('partner_id', [False])
            if isinstance(partner_id_data, list) and len(partner_id_data) > 0:
                candidate_data['partner_id'] = partner_id_data[0]
            else:
                candidate_data['partner_id'] = None
        
        if hasattr(Candidate, 'date_open'):
            candidate_data['date_open'] = CandidateSyncService._parse_odoo_date(
                odoo_candidate.get('date_open')
            )
        
        if hasattr(Candidate, 'date_last_stage_update'):
            candidate_data['date_last_stage_update'] = CandidateSyncService._parse_odoo_date(
                odoo_candidate.get('date_last_stage_update')
            )
        
        # Create or update candidate
        candidate, created = Candidate.objects.update_or_create(
            job=job,
            odoo_candidate_id=odoo_candidate['id'],
            defaults=candidate_data
        )
        
        return candidate
    
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
            logger.warning(f"Could not parse date: {odoo_date_string}")
            return None
    
    @staticmethod
    def sync_candidates_for_company(company, odoo_service=None):
        """Sync all candidates for a company (all jobs)"""
        try:
            logger.info(f"Starting company-wide candidate sync for: {company.company_name}")
            
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
            
            # Get all candidates for the company
            odoo_candidates = odoo_service.get_candidates(company_id=company.odoo_company_id)
            logger.info(f"Found {len(odoo_candidates)} candidates in Odoo for company {company.company_name}")
            
            synced_count = 0
            for odoo_candidate in odoo_candidates:
                try:
                    # Find or create the job first
                    job_id_data = odoo_candidate.get('job_id', [False])
                    if isinstance(job_id_data, list) and len(job_id_data) > 0:
                        odoo_job_id = job_id_data[0]
                        job_name = job_id_data[1] if len(job_id_data) > 1 else 'Unknown Job'
                    else:
                        odoo_job_id = None
                    
                    if odoo_job_id:
                        from job.models import Job
                        job, created = Job.objects.get_or_create(
                            company=company,
                            odoo_job_id=odoo_job_id,
                            defaults={
                                'job_title': job_name,
                                'job_description': '',
                                'state': 'open'
                            }
                        )
                        
                        # Now sync the candidate
                        CandidateSyncService.sync_candidates_for_job(job, odoo_service)
                        synced_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing company candidate: {str(e)}")
                    continue
            
            logger.info(f"Successfully synced {synced_count} candidates for company {company.company_name}")
            
        except Exception as e:
            logger.error(f"Error syncing candidates for company {company.company_name}: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def sync_attachments_for_candidate(candidate, odoo_service):
        """Sync attachments for a single candidate"""
        try:
            # Get attachments for this candidate from Odoo
            attachments = odoo_service.get_attachments(
                res_model='hr.applicant',
                res_id=candidate.odoo_candidate_id
            )
            
            logger.info(f"Found {len(attachments)} attachments for candidate {candidate.name}")
            
            for attachment_data in attachments:
                try:
                    CandidateSyncService._process_single_attachment(candidate, attachment_data, odoo_service)
                except Exception as e:
                    logger.error(f"Error processing attachment {attachment_data.get('id')}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error syncing attachments for candidate {candidate.name}: {str(e)}")
            # Don't raise, continue without attachments

    @staticmethod
    def _process_single_attachment(candidate, attachment_data, odoo_service):
        """Process a single attachment with base64 decoding"""
        attachment_id = attachment_data['id']
        attachment_name = attachment_data.get('name', f'attachment_{attachment_id}')
        attachment_type = attachment_data.get('mimetype', 'application/octet-stream')
        
        # Check if attachment already exists
        if CandidateAttachment.objects.filter(
            candidate=candidate, 
            odoo_attachment_id=attachment_id
        ).exists():
            logger.debug(f"Attachment {attachment_id} already exists for candidate {candidate.name}")
            return
        
        try:
            # Get attachment content with base64 data
            attachment_detail = odoo_service.get_attachment_content(attachment_id)
            
            if attachment_detail and 'datas' in attachment_detail:
                # Decode base64 data
                base64_data = attachment_detail['datas']
                file_content = base64.b64decode(base64_data)
                
                # Get original filename - handle missing datas_fname field
                original_filename = attachment_detail.get('datas_fname', attachment_detail.get('name', f'attachment_{attachment_id}'))
                
                # Get proper file extension
                file_extension = CandidateSyncService._get_file_extension(
                    attachment_detail.get('mimetype'), 
                    original_filename
                )
                
                # Create meaningful filename
                file_name = CandidateSyncService._generate_filename(
                    attachment_name, 
                    file_extension, 
                    attachment_id
                )
                
                # Create attachment record
                attachment = CandidateAttachment(
                    candidate=candidate,
                    odoo_attachment_id=attachment_id,
                    name=attachment_name,
                    file_type=attachment_type,
                    file_size=len(file_content),
                    original_filename=original_filename
                )
                
                # Save file content
                attachment.file.save(file_name, ContentFile(file_content))
                attachment.save()
                
                logger.info(f"Saved attachment: {attachment_name} ({len(file_content)} bytes) for candidate {candidate.name}")
                
            else:
                logger.warning(f"No content found for attachment {attachment_id}")
                # Create record with failed status
                attachment = CandidateAttachment(
                    candidate=candidate,
                    odoo_attachment_id=attachment_id,
                    name=attachment_name,
                    file_type=attachment_type,
                    file_size=0,
                    sync_status='failed',
                    original_filename=attachment_name  # Use attachment name as fallback
                )
                attachment.save()
                
        except Exception as e:
            logger.error(f"Failed to process attachment {attachment_id}: {str(e)}")
            # Create failed attachment record for tracking
            attachment = CandidateAttachment(
                candidate=candidate,
                odoo_attachment_id=attachment_id,
                name=attachment_name,
                file_type=attachment_type,
                file_size=0,
                sync_status='failed',
                original_filename=attachment_name  # Use attachment name as fallback
            )
            attachment.save()

    @staticmethod
    def _get_file_extension(mimetype, original_filename):
        """Get appropriate file extension from mimetype or filename"""
        import mimetypes
        if original_filename:
            # Extract extension from original filename
            _, ext = os.path.splitext(original_filename)
            if ext:
                return ext.lower()
        
        if mimetype:
            # Get extension from mimetype
            ext = mimetypes.guess_extension(mimetype)
            if ext:
                return ext.lower()
        
        # Default extension
        return '.bin'
    
    @staticmethod
    def _generate_filename(attachment_name, file_extension, attachment_id):
        """Generate a safe filename for storage"""
        import re
        # Clean the attachment name
        clean_name = re.sub(r'[^\w\s-]', '', attachment_name)
        clean_name = re.sub(r'[-\s]+', '-', clean_name)
        
        # Ensure filename isn't too long
        if len(clean_name) > 50:
            clean_name = clean_name[:50]
        
        return f"candidate_attachment_{attachment_id}_{clean_name}{file_extension}"
   