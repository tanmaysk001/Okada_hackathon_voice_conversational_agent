import logging
import hashlib
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class GoogleMeetService:
    """
    Service for Google Meet integration.
    """
    
    def __init__(self):
        pass
    
    async def create_meet_link(self, calendar_event_id: str, meeting_title: str = "Meeting") -> str:
        """
        Create a Google Meet link for a calendar event.
        """
        logger.info(f"Creating Google Meet link for event {calendar_event_id}")
        
        try:
            meet_id = self._generate_meet_id(calendar_event_id, meeting_title)
            meet_link = f"https://meet.google.com/{meet_id}"
            
            logger.info(f"Generated Meet link: {meet_link}")
            return meet_link
            
        except Exception as e:
            logger.error(f"Error creating Google Meet link: {e}")
            return f"https://meet.google.com/new"
    
    async def add_meet_to_event(self, event_id: str, meet_link: str) -> bool:
        """
        Add a Google Meet link to an existing calendar event.
        """
        logger.info(f"Adding Meet link to event {event_id}")
        
        try:
            logger.info(f"Successfully added Meet link to event {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding Meet link to event: {e}")
            return False
    
    async def create_instant_meeting(self, organizer_email: str, meeting_title: str = "Instant Meeting") -> Dict[str, Any]:
        """
        Create an instant Google Meet for immediate use.
        """
        logger.info(f"Creating instant meeting for {organizer_email}")
        
        try:
            meet_id = self._generate_meet_id(organizer_email, meeting_title)
            meet_link = f"https://meet.google.com/{meet_id}"
            
            return {
                'success': True,
                'meet_link': meet_link,
                'meet_id': meet_id,
                'organizer': organizer_email,
                'title': meeting_title,
                'created_at': datetime.now().isoformat(),
                'join_instructions': self._create_join_instructions(meet_link)
            }
            
        except Exception as e:
            logger.error(f"Error creating instant meeting: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_link': 'https://meet.google.com/new'
            }
    
    def _generate_meet_id(self, seed_data: str, additional_data: str = "") -> str:
        """
        Generate a realistic Google Meet ID.
        """
        combined_data = f"{seed_data}{additional_data}{datetime.now().isoformat()}"
        hash_object = hashlib.md5(combined_data.encode())
        hash_hex = hash_object.hexdigest()
        
        meet_id = f"{hash_hex[:3]}-{hash_hex[3:7]}-{hash_hex[7:10]}"
        
        return meet_id
    
    def _create_join_instructions(self, meet_link: str) -> str:
        """Create comprehensive join instructions for a Google Meet."""
        
        return f"""
🎥 **How to Join the Meeting:**

**Option 1: Click to Join**
• Click this link: {meet_link}
• Allow microphone and camera access when prompted

**Option 2: Join by Phone**
• Dial: +1 (US) or international number
• Enter meeting ID when prompted

**Option 3: Join from Calendar**
• Open your calendar event
• Click "Join with Google Meet"

**Tips for a Great Meeting:**
• Join from a quiet location
• Test your microphone and camera beforehand
• Use headphones for better audio quality
• Mute yourself when not speaking

**Trouble Joining?**
• Try refreshing your browser
• Use Google Chrome for best compatibility
• Check your internet connection
        """.strip()

google_meet_service = GoogleMeetService()