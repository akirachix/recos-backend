import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from interview.models import Interview

logger = logging.getLogger(__name__)

class InterviewService:
    @staticmethod
    def create_interview_invites(interview):
        try:
            if interview.send_calendar_invite:
                calendar_event = InterviewService._create_calendar_event(interview)
                if calendar_event:
                    interview.google_event_id = calendar_event.get('id')
                    interview.google_calendar_link = calendar_event.get('htmlLink')
                    interview.interview_link = calendar_event.get('hangoutLink')
                    interview.save()
            
            InterviewService._send_email_invites(interview)
            
            interview.status = 'scheduled'
            interview.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create interview invites: {str(e)}")
            return False
    
    @staticmethod
    def _create_calendar_event(interview):
        try:
            recruiter_credentials = interview.recruiter.google_credentials
            if not recruiter_credentials:
                logger.warning("No Google credentials found for recruiter")
                return None
            
            creds = Credentials.from_authorized_user_info(recruiter_credentials)
            service = build('calendar', 'v3', credentials=creds)
            
            attendees = [{'email': interview.recruiter.email}]
            if interview.candidate.email:
                attendees.append({'email': interview.candidate.email})
            
            for team_member in interview.interview_team.all():
                if team_member.email:
                    attendees.append({'email': team_member.email})
            
            event = {
                'summary': f"Interview: {interview.candidate.name} - {interview.job.job_title}",
                'description': interview.description or f"{interview.get_interview_type_display()} with {interview.candidate.name} for {interview.job.job_title} at {interview.company.company_name}",
                'start': {
                    'dateTime': interview.scheduled_at.isoformat(),
                    'timeZone': settings.TIME_ZONE,
                },
                'end': {
                    'dateTime': interview.end_time.isoformat(),
                    'timeZone': settings.TIME_ZONE,
                },
                'attendees': attendees,
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"interview_{interview.id}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                } if interview.is_remote else None,
                'location': interview.location if not interview.is_remote else None,
                'reminders': {
                    'useDefault': True,
                },
            }
            
            event = service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1 if interview.is_remote else 0
            ).execute()
            
            return event
            
        except Exception as e:
            logger.error(f"Google Calendar error: {str(e)}")
            return None
    
    @staticmethod
    def _send_email_invites(interview):
        try:
            if interview.candidate.email:
                candidate_subject = f"Interview Invitation: {interview.job.job_title} at {interview.company.company_name}"
                candidate_context = {
                    'interview': interview,
                    'candidate': interview.candidate,
                    'job': interview.job,
                    'company': interview.company,
                }
                candidate_html = render_to_string('emails/interview_invite_candidate.html', candidate_context)
                candidate_plain = render_to_string('emails/interview_invite_candidate.txt', candidate_context)
                
                send_mail(
                    candidate_subject,
                    candidate_plain,
                    settings.DEFAULT_FROM_EMAIL,
                    [interview.candidate.email],
                    html_message=candidate_html,
                    fail_silently=False,
                )
            
            all_recruiters = [interview.recruiter] + list(interview.interview_team.all())
            for recruiter in all_recruiters:
                if recruiter.email:
                    recruiter_subject = f"Interview Scheduled: {interview.candidate.name} for {interview.job.job_title}"
                    recruiter_context = {
                        'interview': interview,
                        'recruiter': recruiter,
                        'candidate': interview.candidate,
                        'job': interview.job,
                    }
                    recruiter_html = render_to_string('emails/interview_invite_recruiter.html', recruiter_context)
                    recruiter_plain = render_to_string('emails/interview_invite_recruiter.txt', recruiter_context)
                    
                    send_mail(
                        recruiter_subject,
                        recruiter_plain,
                        settings.DEFAULT_FROM_EMAIL,
                        [recruiter.email],
                        html_message=recruiter_html,
                        fail_silently=False,
                    )
                    
        except Exception as e:
            logger.error(f"Email sending error: {str(e)}")
            raise
    
    @staticmethod
    def update_interview_status(interview, status, notes=None, result=None):
        interview.status = status
        if notes:
            interview.notes = notes
        if result:
            interview.result = result
        
        if status == 'completed':
            interview.completed_at = timezone.now()
            
            if result == 'passed' and interview.candidate.odoo_candidate_id:
                InterviewService._update_odoo_candidate_stage(interview)
        
        interview.save()
        return interview
    
    @staticmethod
    def _update_odoo_candidate_stage(interview):
        try:
            pass
        except Exception as e:
            logger.error(f"Failed to update Odoo candidate stage: {str(e)}")