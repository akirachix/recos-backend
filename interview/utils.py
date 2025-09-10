from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import timedelta
import pickle
import os

SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'credentials.json'

def get_simple_login():
    login_info = None
    if os.path.exists('saved_login.pickle'):
        with open('saved_login.pickle', 'rb') as saved_file:
            login_info = pickle.load(saved_file)
    if not login_info or not login_info.valid:
        if login_info and login_info.expired and login_info.refresh_token:
            login_info.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            login_info = flow.run_local_server(port=0)
        with open('saved_login.pickle', 'wb') as saved_file:
            pickle.dump(login_info, saved_file)
    return login_info

def create_google_calendar_event(interview):
    credentials = get_simple_login()
    service = build('calendar', 'v3', credentials=credentials)
    calendar_id = 'primary'

    start_time = interview.scheduled_at.isoformat()
    end_time = (interview.scheduled_at + timedelta(hours=1)).isoformat()

    event = {
        'summary': f'Interview {interview.pk} ({interview.status})',
        'description': 'Interview scheduled via platform',
        'start': {'dateTime': start_time, 'timeZone': 'UTC'},
        'end': {'dateTime': end_time, 'timeZone': 'UTC'},
        'conferenceData': {
            'createRequest': {
                'requestId': f'{interview.pk}-meet',
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    created_event = service.events().insert(
        calendarId=calendar_id,
        body=event,
        conferenceDataVersion=1,
        sendUpdates='all'
    ).execute()

    event_id = created_event.get('id')
    hangout_link = created_event.get('hangoutLink')
    return event_id, hangout_link