import datetime as dt
import uuid
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.models.crm_models import AppointmentData

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """
    Initializes and returns the Google Calendar API service client
    using Service Account credentials.
    """
    creds = None
    credentials_path = settings.GOOGLE_APPLICATION_CREDENTIALS

    if not credentials_path:
        raise ValueError("The GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")

    try:
        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
        service = build("calendar", "v3", credentials=creds)
        return service
    except FileNotFoundError:
        raise ValueError(f"Service account key file not found at: {credentials_path}")
    except Exception as e:
        raise ValueError(f"Failed to initialize Google Calendar service: {e}")

def create_calendar_event(appointment_data: AppointmentData, user_email: str) -> str:
    """Schedules a new event on Google Calendar using a structured AppointmentData object."""
    try:
        service = get_calendar_service()
        
        start_time = appointment_data.date
        end_time = start_time + dt.timedelta(minutes=appointment_data.duration_minutes)

        attendees = [{'email': email} for email in appointment_data.attendee_emails]
        attendees.append({'email': user_email}) # Add the main user

        event = {
            "summary": appointment_data.title,
            "location": appointment_data.location,
            "description": appointment_data.description or f"Okada appointment for {user_email}.",
            "start": {"dateTime": start_time.isoformat(), "timeZone": "America/New_York"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "America/New_York"},
            "attendees": attendees,
            "conferenceData": {
                "createRequest": {
                    "requestId": f"{uuid.uuid4().hex}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 30}],
            },
        }

        created_event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1).execute()
        print(f"Event created: {created_event.get('htmlLink')}")
        return created_event.get('hangoutLink') # Return the Google Meet link

    except Exception as e:
        print(f"An unexpected error occurred during scheduling: {e}")
        raise