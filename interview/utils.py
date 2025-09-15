import logging
import json
import pickle
import os
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, 'credentials.json')


class GoogleCalendarService:

    AI_ASSISTANT_EMAIL = getattr(settings, 'AI_ASSISTANT_EMAIL', 'linmercymuthoni@gmail.com')
    AI_ASSISTANT_NAME = getattr(settings, 'AI_ASSISTANT_NAME', 'Recos AI Assistant')

    @staticmethod
    def is_production():
        return 'DYNO' in os.environ or os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('production')

    @classmethod
    def get_oauth_client_config(cls):
        """Get OAuth client configuration - always use web flow for consistency"""
        if cls.is_production():
            redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', 'https://recos-662b3d74caf2.herokuapp.com/auth/google/callback/')
        else:
            redirect_uri = 'http://localhost:8000/auth/google/callback/'
        
        return {
            "web": {
                "client_id": os.environ['GOOGLE_CLIENT_ID'],
                "project_id": os.environ['GOOGLE_PROJECT_ID'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": os.environ['GOOGLE_CLIENT_SECRET'],
                "redirect_uris": [redirect_uri],
                "javascript_origins": [os.environ.get('SITE_DOMAIN', 'https://recos-662b3d74caf2.herokuapp.com')],
            }
        }

    @classmethod
    def get_redirect_uri(cls, request):
        """Get the correct redirect URI for current environment"""
        if cls.is_production():
            return os.environ.get('GOOGLE_REDIRECT_URI', 'https://recos-662b3d74caf2.herokuapp.com/auth/google/callback/')
        else:
            return request.build_absolute_uri(reverse('google_auth_callback'))
    @classmethod
    def get_authorization_url(cls, request, user):
        """Generate authorization URL for OAuth flow"""
        try:
            client_config = cls.get_oauth_client_config()
            redirect_uri = cls.get_redirect_uri(request)
            
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )
            
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            request.session['google_oauth_state'] = state
            request.session['google_oauth_user_id'] = user.id
            request.session['google_oauth_redirect_uri'] = redirect_uri
            
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {str(e)}")
            raise

    @classmethod
    def exchange_code_for_token(cls, request):
        """Exchange authorization code for tokens"""
        try:
            code = request.GET.get('code')
            state = request.GET.get('state')
            stored_state = request.session.get('google_oauth_state')
            user_id = request.session.get('google_oauth_user_id')
            redirect_uri = request.session.get('google_oauth_redirect_uri')
            
            if not code:
                raise RuntimeError("No authorization code provided")
            
            if not state or state != stored_state:
                raise RuntimeError("Invalid state parameter")
            
            if not user_id:
                raise RuntimeError("No user ID in session")
            
            if not redirect_uri:
                raise RuntimeError("No redirect URI in session")
            
            client_config = cls.get_oauth_client_config()
            
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=redirect_uri,
                state=state
            )
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            credentials_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
            request.session[f'google_credentials_{user_id}'] = credentials_dict
            
            request.session.pop('google_oauth_state', None)
            request.session.pop('google_oauth_user_id', None)
            request.session.pop('google_oauth_redirect_uri', None)
            
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to exchange code for token: {str(e)}")
            raise

    @staticmethod
    def _create_credentials_file_if_needed():
        if not os.path.exists(CREDENTIALS_PATH):
            credentials_data = {
                "installed": {
                    "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
                    "project_id": os.environ.get('GOOGLE_PROJECT_ID'),
                    "auth_uri": os.environ.get('GOOGLE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
                    "token_uri": os.environ.get('GOOGLE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET'),
                    "redirect_uris": [os.environ.get('GOOGLE_REDIRECT_URIS', 'http://localhost')]
                }
            }
            with open(CREDENTIALS_PATH, 'w') as f:
                json.dump(credentials_data, f, indent=2)
            logger.info(f"Created {CREDENTIALS_PATH} from environment variables")

    @classmethod
    def get_credentials_from_session(cls, request, user_id):
        """Get credentials from session storage"""
        creds_dict = request.session.get(f'google_credentials_{user_id}')
        if not creds_dict:
            return None
        
        try:
            return Credentials(
                token=creds_dict['token'],
                refresh_token=creds_dict['refresh_token'],
                token_uri=creds_dict['token_uri'],
                client_id=creds_dict['client_id'],
                client_secret=creds_dict['client_secret'],
                scopes=creds_dict['scopes']
            )
        except Exception as e:
            logger.error(f"Failed to create credentials from session: {str(e)}")
            return None

    @classmethod
    def get_credentials(cls, request, user):
        """Get credentials - uses session for production, local files for development"""
        try:
            if cls.is_production():
                credentials = cls.get_credentials_from_session(request, user.id)
                
                if not credentials:
                    auth_url = cls.get_authorization_url(request, user)
                    raise RuntimeError(f"Google authentication required. Please visit: {auth_url}")
                
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                    creds_dict = {
                        'token': credentials.token,
                        'refresh_token': credentials.refresh_token,
                        'token_uri': credentials.token_uri,
                        'client_id': credentials.client_id,
                        'client_secret': credentials.client_secret,
                        'scopes': credentials.scopes,
                        'expiry': credentials.expiry.isoformat() if credentials.expiry else None
                    }
                    request.session[f'google_credentials_{user.id}'] = creds_dict
                
                return credentials
            else:
                cls._create_credentials_file_if_needed()
                
                token_path = f'token_{user.id}.pickle'
                
                credentials = None
                if os.path.exists(token_path):
                    with open(token_path, 'rb') as token:
                        credentials = pickle.load(token)
                
                if not credentials or not credentials.valid:
                    if credentials and credentials.expired and credentials.refresh_token:
                        credentials.refresh(Request())
                    else:
                        if not os.path.exists(CREDENTIALS_PATH):
                            raise FileNotFoundError(f"Google credentials file not found at {CREDENTIALS_PATH}")

                        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                        credentials = flow.run_local_server(port=0)

                    with open(token_path, 'wb') as token:
                        pickle.dump(credentials, token)

                return credentials
                
        except Exception as e:
            logger.error(f"Failed to get Google credentials: {str(e)}")
            raise
        
    @classmethod
    def create_interview_event(cls, request, interview, send_notifications=True):
        try:
            credentials = cls.get_credentials(request, interview.recruiter)
            service = build('calendar', 'v3', credentials=credentials)

            end_time = interview.scheduled_at + timedelta(minutes=interview.duration)
            attendees = cls._build_interview_attendees(interview)

            event = {
                'summary': f"Interview: {interview.candidate.name} - {interview.title}",
                'description': cls._build_interview_description(interview),
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
                        'requestId': f"interview_{interview.interview_id}_{int(timezone.now().timestamp())}",
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
                        'interviewId': str(interview.interview_id),
                        'candidateId': str(interview.candidate.candidate_id),
                        'aiAnalysisEnabled': 'true',
                        'aiAssistantEmail': cls.AI_ASSISTANT_EMAIL
                    }
                }
            }

            created_event = service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendUpdates='all' if send_notifications else 'none'
            ).execute()

            event_info = {
                'event_id': created_event.get('id'),
                'meet_link': created_event.get('hangoutLink'),
                'event_link': created_event.get('htmlLink'),
                'conference_id': created_event.get('conferenceData', {}).get('conferenceId'),
                'ai_join_url': cls._generate_ai_meet_url(created_event, interview)
            }

            logger.info(f"Created interview event with AI assistant: {event_info['event_id']}")
            return event_info

        except Exception as e:
            logger.error(f"Failed to create interview event: {str(e)}")
            raise

    @staticmethod
    def _build_interview_attendees(interview):
        """Build attendees list with email validation"""
        attendees = []
        
        if interview.recruiter and interview.recruiter.email:
            attendees.append({
                'email': interview.recruiter.email.strip().lower(),
                'displayName': interview.recruiter.get_full_name(),
                'organizer': True,
                'responseStatus': 'accepted'
            })
        else:
            logger.warning(f"Missing recruiter email for interview {interview.interview_id}")
        
        ai_email = GoogleCalendarService.AI_ASSISTANT_EMAIL.strip().lower()
        if ai_email and '@' in ai_email:
            attendees.append({
                'email': ai_email,
                'displayName': GoogleCalendarService.AI_ASSISTANT_NAME,
                'responseStatus': 'accepted',
                'optional': False,
                'comment': 'AI Analysis Assistant - Provides real-time feedback and analysis'
            })
        else:
            logger.error(f"Invalid AI assistant email: {ai_email}")
        
        if interview.candidate and interview.candidate.email:
            attendees.append({
                'email': interview.candidate.email.strip().lower(),
                'displayName': interview.candidate.name,
                'responseStatus': 'needsAction',
                'optional': False
            })
        else:
            logger.warning(f"Missing candidate email for interview {interview.interview_id}")
        
        logger.info(f"Built attendees: {attendees}")
        return attendees

    @staticmethod
    def _build_interview_description(interview):
        description = f"""
Interview Details
Title: {interview.title}
Candidate: {interview.candidate.name} ({interview.candidate.email})
Duration: {interview.duration} minutes
Status: {interview.get_status_display()}

Participants
- Recruiter: {interview.recruiter.get_full_name()} ({interview.recruiter.email})
- Candidate: {interview.candidate.name}
- AI Assistant: {GoogleCalendarService.AI_ASSISTANT_NAME} 

AI Assistant Features
- Real-time conversation analysis
- Skill assessment tracking
- Behavioral pattern recognition
- Interview quality scoring
- Automated note-taking

Interview Agenda
1. Introduction & welcome (5 minutes)
2. Technical assessment (15 minutes)
3. Cultural fit discussion (10 minutes)
4. Candidate questions (5 minutes)
5. Next steps & closing (5 minutes)

Privacy Notice
This interview will be recorded and analyzed by our AI assistant to improve the hiring process. 
All data is encrypted and stored securely in compliance with privacy regulations.

{interview.description or 'No additional description provided.'}

Technical Support
If you experience any issues joining the meeting, please contact IT support.

**Preparation Required**
{interview.required_preparation or 'No specific preparation required.'}
"""
        return description.strip()

    @classmethod
    def _generate_ai_meet_url(cls, event_data, interview):
        meet_link = event_data.get('hangoutLink', '')
        if meet_link:
            params = {
                'ai_analysis': 'true',
                'interview_id': str(interview.interview_id),
                'candidate_id': str(interview.candidate.candidate_id),
                'assistant_email': cls.AI_ASSISTANT_EMAIL,
                'enable_screen_share': 'true',
                'enable_chat': 'true',
                'enable_recording': 'true'
            }
            param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            return f"{meet_link}?{param_string}"
        return meet_link

    @classmethod
    def enable_ai_features(cls, event_id, interview):
        try:
            credentials = cls.get_credentials(interview.recruiter)
            service = build('calendar', 'v3', credentials=credentials)

            event = service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()

            if 'extendedProperties' not in event:
                event['extendedProperties'] = {}
            if 'private' not in event['extendedProperties']:
                event['extendedProperties']['private'] = {}
            event['extendedProperties']['private'].update({
                'enableAiAssistant': 'true',
                'aiAssistantEmail': cls.AI_ASSISTANT_EMAIL,
                'allowScreenShare': 'true',
                'allowRecording': 'true',
                'enableRealTimeAnalysis': 'true',
                'showAiOverlay': 'true'
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

    @classmethod
    def get_meeting_analytics(cls, event_id, interview):
        try:
            credentials = cls.get_credentials(interview.recruiter)
            service = build('calendar', 'v3', credentials=credentials)

            event = service.events().get(
                calendarId='primary',
                eventId=event_id,
                fields='conferenceData,attendees'
            ).execute()

            attendees_joined = [
                attendee['email']
                for attendee in event.get('attendees', [])
                if attendee.get('responseStatus') == 'accepted'
            ]

            return {
                'meeting_details': {
                    'meet_id': event.get('conferenceData', {}).get('conferenceId'),
                    'meet_link': event.get('hangoutLink'),
                    'recording_available': False,
                    'participants_joined': attendees_joined
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

    @classmethod
    def update_interview_event(cls, interview):
        try:
            if not interview.google_event_id:
                raise ValueError("No Google event ID associated with this interview")

            credentials = cls.get_credentials(interview.recruiter)
            service = build('calendar', 'v3', credentials=credentials)

            end_time = interview.scheduled_at + timedelta(minutes=interview.duration)
            attendees = cls._build_interview_attendees(interview)

            event = {
                'summary': f"Interview: {interview.candidate.name} - {interview.title}",
                'description': cls._build_interview_description(interview),
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

    @classmethod
    def cancel_interview_event(cls, interview):
        try:
            if not interview.google_event_id:
                raise ValueError("No Google event ID associated with this interview")

            credentials = cls.get_credentials(interview.recruiter)
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


def create_google_calendar_event(interview):
    result = GoogleCalendarService.create_interview_event(interview)
    return result['event_id'], result['meet_link']