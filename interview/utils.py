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

    AI_ASSISTANT_EMAIL = getattr(settings, 'AI_ASSISTANT_EMAIL', 'muthonimercylin@gmail.com')
    AI_ASSISTANT_NAME = getattr(settings, 'AI_ASSISTANT_NAME', 'Recos AI Assistant')

    @staticmethod
    def is_production():
        return 'DYNO' in os.environ or os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('production')

    @classmethod
    def get_oauth_client_config(cls):
        if cls.is_production():
            return {
                "web": {
                    "client_id": os.environ['GOOGLE_CLIENT_ID'],
                    "project_id": os.environ['GOOGLE_PROJECT_ID'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": os.environ['GOOGLE_CLIENT_SECRET'],
                    "redirect_uris": [os.environ.get('GOOGLE_REDIRECT_URI')],
                    "javascript_origins": [os.environ.get('SITE_DOMAIN')],
                }
            }
        else:
            cred_path = os.path.join(settings.BASE_DIR, "credentials.json")
            with open(cred_path) as f:
                return json.load(f)

    @classmethod
    def get_redirect_uri(cls, request):
        if cls.is_production():
            return os.environ.get('GOOGLE_REDIRECT_URI')
        else:
            return request.build_absolute_uri(reverse('google_auth_callback'))

    @classmethod
    def get_authorization_url(cls, request, user):
        flow = Flow.from_client_config(
            cls.get_oauth_client_config(),
            scopes=SCOPES,
            redirect_uri=cls.get_redirect_uri(request)
        )
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        request.session['google_oauth_state'] = state
        request.session['google_oauth_user_id'] = user.id
        return auth_url

    @classmethod
    def exchange_code_for_token(cls, request, code):
        state = request.session.get('google_oauth_state')
        user_id = request.session.get('google_oauth_user_id')
        if not state or not user_id:
            raise RuntimeError("Invalid OAuth session")
        flow = Flow.from_client_config(
            cls.get_oauth_client_config(),
            scopes=SCOPES,
            redirect_uri=cls.get_redirect_uri(request),
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
        return credentials

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
                    "redirect_uris": [os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost')]
                }
            }
            with open(CREDENTIALS_PATH, 'w') as f:
                json.dump(credentials_data, f, indent=2)
            logger.info(f"Created {CREDENTIALS_PATH} from environment variables")

    @classmethod
    def get_credentials(cls, user=None):
        try:
            cls._create_credentials_file_if_needed()
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
                    if not os.path.exists(CREDENTIALS_PATH):
                        raise FileNotFoundError(f"Google credentials file not found at {CREDENTIALS_PATH}")

                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)

                    if cls.is_production():
                        auth_url, _ = flow.authorization_url(prompt='consent')
                        raise RuntimeError(f"Manual authentication required. Please visit: {auth_url}")
                    else:
                        credentials = flow.run_local_server(port=0)

                with open(token_path, 'wb') as token:
                    pickle.dump(credentials, token)

            return credentials
        except Exception as e:
            logger.error(f"Failed to get Google credentials: {str(e)}")
            raise

    @classmethod
    def create_interview_event(cls, interview, send_notifications=True):
        try:
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
        attendees = [
            {
                'email': interview.recruiter.email,
                'displayName': interview.recruiter.get_full_name(),
                'responseStatus': 'accepted'
            },
            {
                'email': GoogleCalendarService.AI_ASSISTANT_EMAIL,
                'displayName': GoogleCalendarService.AI_ASSISTANT_NAME,
                'responseStatus': 'accepted',
                'optional': False,
                'comment': 'AI Analysis Assistant - Provides real-time feedback and analysis'
            },
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
        description = f"""
Interview Details
Title: {interview.title}
Candidate: {interview.candidate.name} ({interview.candidate.email})
Duration: {interview.duration} minutes
Status: {interview.get_status_display()}

Participants
- Recruiter: {interview.recruiter.get_full_name()} ({interview.recruiter.email})
- Candidate: {interview.candidate.name}
- AI Assistant: {GoogleCalendarService.AI_ASSISTANT_NAME} (Analysis & Recording)

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