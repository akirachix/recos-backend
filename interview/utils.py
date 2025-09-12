import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import timedelta
import pickle
import os
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_PATH = 'credentials.json'

class GoogleCalendarService:
    
    # AI Assistant configuration
    AI_ASSISTANT_EMAIL = getattr(settings, 'AI_ASSISTANT_EMAIL', 'muthonimercylin@gmail.com')
    AI_ASSISTANT_NAME = getattr(settings, 'AI_ASSISTANT_NAME', 'Recos AI Assistant')
    
    @staticmethod
    def get_credentials(user=None):
        """Get Google credentials for a user"""
        try:
            credentials_path =  'credentials.json'
            # Use user-specific token file if user is provided
            if user:
                token_path = f'token_{user.id}.pickle'
            else:
                token_path = 'token.pickle'
            
            credentials = None
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    credentials = pickle.load(token)
            
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    if not os.path.exists(credentials_path):
                        raise FileNotFoundError(f"Google credentials file not found at {credentials_path}")
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                    credentials = flow.run_local_server(port=0)
                
                with open(token_path, 'wb') as token:
                    pickle.dump(credentials, token)
            
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to get Google credentials: {str(e)}")
            raise
    
    @staticmethod
    def create_interview_event(interview, send_notifications=True):
        """
        Create Google Calendar event for an interview with AI assistant using Google Meet
        """
        try:
            credentials = GoogleCalendarService.get_credentials(interview.recruiter)
            service = build('calendar', 'v3', credentials=credentials)
            
            # Calculate end time
            end_time = interview.scheduled_at + timedelta(minutes=interview.duration)
            
            # Build attendees including AI assistant
            attendees = GoogleCalendarService._build_interview_attendees(interview)
            
            event = {
                'summary': f"Interview: {interview.candidate.name} - {interview.title}",
                'description': GoogleCalendarService._build_interview_description(interview),
                'start': {
                    'dateTime': interview.scheduled_at.isoformat(),
                    'timeZone': str(interview.scheduled_at.tzinfo) if interview.scheduled_at.tzinfo else 'UTC'
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': str(end_time.tzinfo) if end_time.tzinfo else 'UTC'
                },
                'attendees': attendees,
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"interview_{interview.id}_{int(timezone.now().timestamp())}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                    }
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 30},
                    ],
                },
                'guestsCanInviteOthers': False,
                'guestsCanModify': False,
                'guestsCanSeeOtherGuests': True,
                'transparency': 'opaque',
                'visibility': 'private',
                'extendedProperties': {
                    'private': {
                        'interviewId': str(interview.id),
                        'candidateId': str(interview.candidate.candidate_id),
                        'aiAnalysisEnabled': 'true',
                        'aiAssistantEmail': GoogleCalendarService.AI_ASSISTANT_EMAIL
                    }
                }
            }
            
            # Create the event with Google Meet conference
            created_event = service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendUpdates='all' if send_notifications else 'none'
            ).execute()
            
            # Extract event details
            event_info = {
                'event_id': created_event.get('id'),
                'meet_link': created_event.get('hangoutLink'),
                'event_link': created_event.get('htmlLink'),
                'conference_id': created_event.get('conferenceData', {}).get('conferenceId'),
                'ai_join_url': GoogleCalendarService._generate_ai_meet_url(created_event, interview)
            }
            
            logger.info(f"Created interview event with AI assistant: {event_info['event_id']}")
            
            return event_info
            
        except Exception as e:
            logger.error(f"Failed to create interview event: {str(e)}")
            raise
    
    @staticmethod
    def _build_interview_attendees(interview):
        """Build attendees list including AI assistant with proper Google Meet permissions"""
        attendees = [
            # Recruiter (organizer)
            {
                'email': interview.recruiter.email,
                'displayName': interview.recruiter.get_full_name(),
                'organizer': True,
                'responseStatus': 'accepted'
            },
            
            # AI Assistant
            {
                'email': GoogleCalendarService.AI_ASSISTANT_EMAIL,
                'displayName': GoogleCalendarService.AI_ASSISTANT_NAME,
                'responseStatus': 'accepted',
                'optional': False,
                'comment': 'AI Analysis Assistant - Provides real-time feedback and analysis'
            },
            
            # Candidate
            {
                'email': interview.candidate.email,
                'displayName': interview.candidate.name,
                'responseStatus': 'needsAction',
                'optional': False
            }
        ]
        
        return attendees
    
    @staticmethod
    def _build_interview_description(interview):
        """Build detailed interview description with AI instructions"""
        description = f"""
**Interview Details**
Title: {interview.title}
Candidate: {interview.candidate.name} ({interview.candidate.email})
Duration: {interview.duration} minutes
Status: {interview.get_status_display()}

**Participants**
- Recruiter: {interview.recruiter.get_full_name()} ({interview.recruiter.email})
- Candidate: {interview.candidate.name}
- AI Assistant: {GoogleCalendarService.AI_ASSISTANT_NAME} (Analysis & Recording)

**AI Assistant Features**
- Real-time conversation analysis
- Skill assessment tracking
- Behavioral pattern recognition
- Interview quality scoring
- Automated note-taking

**Interview Agenda**
1. Introduction & welcome (5 minutes)
2. Technical assessment (15 minutes)
3. Cultural fit discussion (10 minutes)
4. Candidate questions (5 minutes)
5. Next steps & closing (5 minutes)

**Privacy Notice**
This interview will be recorded and analyzed by our AI assistant to improve the hiring process. 
All data is encrypted and stored securely in compliance with privacy regulations.

{interview.description or 'No additional description provided.'}

**Technical Support**
If you experience any issues joining the meeting, please contact IT support.

**Preparation Required**
{interview.required_preparation or 'No specific preparation required.'}
"""
        return description.strip()
    
    @staticmethod
    def _generate_ai_meet_url(event_data, interview):
        """Generate special join URL for AI assistant with Google Meet parameters"""
        meet_link = event_data.get('hangoutLink', '')
        if meet_link:
            # Add parameters for AI analysis and interaction capabilities
            params = {
                'ai_analysis': 'true',
                'interview_id': str(interview.id),
                'candidate_id': str(interview.candidate.candidate_id),
                'assistant_email': GoogleCalendarService.AI_ASSISTANT_EMAIL,
                'enable_screen_share': 'true',
                'enable_chat': 'true',
                'enable_recording': 'true'
            }
            
            param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            return f"{meet_link}?{param_string}"
        return meet_link
    
    @staticmethod
    def enable_ai_features(event_id, interview):
        """Enable AI-specific features for Google Meet"""
        try:
            credentials = GoogleCalendarService.get_credentials(interview.recruiter)
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get current event
            event = service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            # Update with AI-specific parameters for Google Meet
            if 'conferenceData' not in event:
                event['conferenceData'] = {}
            
            if 'parameters' not in event['conferenceData']:
                event['conferenceData']['parameters'] = {}
            
            # Add AI-specific parameters for Google Meet
            event['conferenceData']['parameters'].update({
                'addOnParameters': {
                    'parameters': {
                        'enableAiAssistant': 'true',
                        'aiAssistantEmail': GoogleCalendarService.AI_ASSISTANT_EMAIL,
                        'allowScreenShare': 'true',
                        'allowRecording': 'true',
                        'enableRealTimeAnalysis': 'true',
                        'showAiOverlay': 'true'
                    }
                }
            })
            
            updated_event = service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event,
                conferenceDataVersion=1
            ).execute()
            
            logger.info(f"Enabled AI features for Google Meet event: {event_id}")
            return updated_event
            
        except Exception as e:
            logger.error(f"Failed to enable AI features: {str(e)}")
            raise
    
    @staticmethod
    def get_meeting_analytics(event_id, interview):
        """Retrieve meeting analytics from Google Meet"""
        try:
            credentials = GoogleCalendarService.get_credentials(interview.recruiter)
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get event details including Meet participation data
            event = service.events().get(
                calendarId='primary',
                eventId=event_id,
                fields='conferenceData,attendeesResponseStatus'
            ).execute()
            
            # This would integrate with our AI model
            return {
                'meeting_details': {
                    'meet_id': event.get('conferenceData', {}).get('conferenceId'),
                    'meet_link': event.get('hangoutLink'),
                    'recording_available': False,
                    'participants_joined': []
                },
                'ai_analysis': {
                    'conversation_metrics': {},
                    'sentiment_scores': {},
                    'skill_assessment': {},
                    'recommendations': []
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get meeting analytics: {str(e)}")
            return None
    
    @staticmethod
    def update_interview_event(interview):
        """Update an existing Google Calendar event"""
        try:
            if not interview.google_event_id:
                raise ValueError("No Google event ID associated with this interview")
                
            credentials = GoogleCalendarService.get_credentials(interview.recruiter)
            service = build('calendar', 'v3', credentials=credentials)
            
            # Calculate end time
            end_time = interview.scheduled_at + timedelta(minutes=interview.duration)
            
            # Build attendees including AI assistant
            attendees = GoogleCalendarService._build_interview_attendees(interview)
            
            event = {
                'summary': f"Interview: {interview.candidate.name} - {interview.title}",
                'description': GoogleCalendarService._build_interview_description(interview),
                'start': {
                    'dateTime': interview.scheduled_at.isoformat(),
                    'timeZone': str(interview.scheduled_at.tzinfo) if interview.scheduled_at.tzinfo else 'UTC'
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': str(end_time.tzinfo) if end_time.tzinfo else 'UTC'
                },
                'attendees': attendees
            }
            
            updated_event = service.events().update(
                calendarId='primary',
                eventId=interview.google_event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            logger.info(f"Updated interview event: {interview.google_event_id}")
            return updated_event
            
        except Exception as e:
            logger.error(f"Failed to update interview event: {str(e)}")
            raise
    
    @staticmethod
    def cancel_interview_event(interview):
        """Cancel a Google Calendar event"""
        try:
            if not interview.google_event_id:
                raise ValueError("No Google event ID associated with this interview")
                
            credentials = GoogleCalendarService.get_credentials(interview.recruiter)
            service = build('calendar', 'v3', credentials=credentials)
            
            service.events().delete(
                calendarId='primary',
                eventId=interview.google_event_id,
                sendUpdates='all'
            ).execute()
            
            logger.info(f"Cancelled interview event: {interview.google_event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel interview event: {str(e)}")
            raise

# Backward compatibility function
def create_google_calendar_event(interview):
    """Legacy function for backward compatibility"""
    result = GoogleCalendarService.create_interview_event(interview)
    return result['event_id'], result['meet_link']