import logging
import re
import json
import uuid
import dateparser
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from llama_index.core.llms import ChatMessage
from llama_index.core import Settings

from app.models.crm_models import (
    AppointmentSession, AppointmentData, AppointmentStatus, 
    WorkflowResponse, ConfirmationUI, AppointmentError, AppointmentIntent
)
from app.services.database_service import get_database
from app.core.logging_config import logger

class AppointmentIntentDetectionService:
    APPOINTMENT_TRIGGERS = [
        r"\b(book|schedule|set up|arrange|make)\s+(an?\s+)?(appointment|meeting|call|session)\b",
        r"\bi\s+(want|need|would like)\s+to\s+(book|schedule|set up|arrange|make)",
        r"\b(can|could)\s+(i|we)\s+(book|schedule|set up|arrange|make)",
        r"\b(let's|lets)\s+(meet|schedule|set up a meeting)\b",
        r"\b(need|want)\s+to\s+(meet|have a meeting)\b",
        r"\b(schedule|set up)\s+(a|the)\s+(meeting|call|appointment)\b",
        r"\b(free|available)\s+(on|at|for|tomorrow|next week|this week)\b",
        r"\b(when\s+(can|are you)\s+)?(available|free)\b",
        r"\bmeet\s+(on|at|tomorrow|next week|this week)\b",
        r"\b(put it in|add to|block)\s+(my|the)\s+calendar\b",
        r"\bcalendar\s+(invite|invitation|meeting)\b",
        r"\bsend\s+(me\s+)?(a\s+)?(calendar\s+)?(invite|invitation)\b"
    ]
    
    DETAIL_PATTERNS = {
        'date': [
            r"\b(tomorrow|today|next week|this week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}(st|nd|rd|th)?\s+(of\s+)?\w+)\b",
            r"\bon\s+(\w+,?\s*\w*\s*\d{1,2}(st|nd|rd|th)?)\b"
        ],
        'time': [
            r"\b(\d{1,2}(:\d{2})?\s*(am|pm|AM|PM))\b",
            r"\bat\s+(\d{1,2}(:\d{2})?\s*(am|pm|AM|PM)?)\b",
            r"\b(morning|afternoon|evening|noon)\b"
        ],
        'location': [
            r"\bat\s+(the\s+)?(office|building|location|address|room\s+\d+)\b",
            r"\bin\s+(the\s+)?(conference room|meeting room|office)\b",
            # More specific address regex to avoid false positives
            r"\b(\d+\s+[a-zA-Z0-9\s,.-]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|ln|lane|ct|court|pl|place))\b"
        ],
        'email': [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            r"\bwith\s+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b"
        ],
        'title': [
            r"\b(meeting|appointment|call|session)\s+(about|for|regarding)\s+(.+)",
            r"\b(.+)\s+(meeting|appointment|call|session)\b"
        ]
    }
    
    def __init__(self):
        pass
    
    async def detect_appointment_intent(self, message: str) -> AppointmentIntent:
        logger.info(f"Analyzing message for appointment intent: '{message}'")
        pattern_confidence = self._calculate_pattern_confidence(message)
        llm_confidence = await self._llm_intent_classification(message)
        combined_confidence = (pattern_confidence * 0.7) + (llm_confidence * 0.3)
        extracted_details = {}
        missing_fields = []
        if combined_confidence > 0.6:
            extracted_details = self.extract_appointment_details(message)
            missing_fields = self._identify_missing_fields(extracted_details)
        is_appointment_request = combined_confidence > 0.6
        logger.info(f"Appointment intent detection: {is_appointment_request} (confidence: {combined_confidence:.2f})")
        return AppointmentIntent(
            is_appointment_request=is_appointment_request,
            confidence=combined_confidence,
            extracted_details=extracted_details,
            missing_fields=missing_fields
        )
    
    def extract_appointment_details(self, message: str) -> Dict[str, Any]:
        """Extracts appointment details using a combination of regex and dateparser."""
        details = {}
        message_lower = message.lower()

        # Use dateparser for robust date/time extraction
        parsed_date = dateparser.parse(message, settings={'PREFER_DATES_FROM': 'future', 'RETURN_AS_TIMEZONE_AWARE': False})
        if parsed_date:
            details['datetime'] = parsed_date
            details['date'] = parsed_date.strftime('%Y-%m-%d')
            details['time'] = parsed_date.strftime('%I:%M %p')

        # Use regex for other details
        for detail_type, patterns in self.DETAIL_PATTERNS.items():
            # Skip date/time as it's handled by dateparser
            if detail_type in ['date', 'time']:
                continue

            for pattern in patterns:
                matches = re.findall(pattern, message_lower, re.IGNORECASE)
                if matches:
                    if detail_type == 'email':
                        details[detail_type] = [match if isinstance(match, str) else match[0] for match in matches]
                    else:
                        # Handle cases where regex returns tuples from capture groups
                        match_value = matches[0] if isinstance(matches[0], str) else matches[0][0]
                        details[detail_type] = match_value.strip()
                    break # Move to the next detail type once a match is found

        logger.info(f"Extracted appointment details: {details}")
        return details
    
    def _calculate_pattern_confidence(self, message: str) -> float:
        message_lower = message.lower()
        trigger_matches = 0
        for pattern in self.APPOINTMENT_TRIGGERS:
            if re.search(pattern, message_lower):
                trigger_matches += 1
        if trigger_matches > 0:
            base_confidence = min(0.8, 0.4 + (trigger_matches * 0.2))
        else:
            base_confidence = 0.0
        detail_boost = 0.0
        for detail_type, patterns in self.DETAIL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    detail_boost += 0.1
                    break
        total_confidence = min(1.0, base_confidence + detail_boost)
        logger.debug(f"Pattern confidence: {total_confidence:.2f} (triggers: {trigger_matches}, detail_boost: {detail_boost:.1f})")
        return total_confidence
    
    async def _llm_intent_classification(self, message: str) -> float:
        classification_prompt = f"""Analyze this message to determine if the user wants to book, schedule, or arrange an appointment, meeting, or call. Respond with only a number between 0.0 and 1.0 representing confidence that this is an appointment booking request."""
        try:
            response = await Settings.llm.achat([ChatMessage(role="user", content=classification_prompt)])
            confidence_text = response.message.content.strip() if response.message.content else "0.0"
            confidence_match = re.search(r'(\d+\.?\d*)', confidence_text)
            if confidence_match:
                confidence = float(confidence_match.group(1))
                confidence = max(0.0, min(1.0, confidence))
                logger.debug(f"LLM classification confidence: {confidence:.2f}")
                return confidence
            else:
                logger.warning(f"Could not parse LLM confidence from: {confidence_text}")
                return 0.0
        except Exception as e:
            logger.error(f"Error in LLM intent classification: {e}")
            return 0.0
    
    def _identify_missing_fields(self, extracted_details: Dict[str, Any]) -> List[str]:
        required_fields = ['title', 'date', 'time', 'location']
        missing = []
        for field in required_fields:
            if field not in extracted_details or not extracted_details[field]:
                missing.append(field)
        if 'title' in missing:
            missing.remove('title')
        logger.debug(f"Missing appointment fields: {missing}")
        return missing

appointment_intent_detection_service = AppointmentIntentDetectionService()

class AppointmentWorkflowManager:
    def __init__(self):
        pass
    
    async def start_appointment_booking(self, user_id: str, message: str) -> WorkflowResponse:
        logger.info(f"Starting appointment booking for user {user_id}")
        try:
            intent_result = await apointment_intent_detection_service.detect_appointment_intent(message)
            appointment_data = AppointmentData(
                title="Meeting",
                location="",
                date=datetime.now(),
                organizer_email=user_id
            )
            self._apply_extracted_details(appointment_data, intent_result.extracted_details)
            session_id = str(uuid.uuid4())
            session = AppointmentSession(
                session_id=session_id,
                user_id=user_id,
                status=AppointmentStatus.COLLECTING_INFO,
                collected_data=appointment_data,
                missing_fields=intent_result.missing_fields
            )
            await self._save_session(session)
            return await self._get_next_workflow_step(session)
        except Exception as e:
            logger.error(f"Error starting appointment booking: {e}")
            return WorkflowResponse(
                success=False,
                message="Sorry, I encountered an issue starting the appointment booking. Please try again.",
                error_details=AppointmentError(
                    error_type="WORKFLOW_START_ERROR",
                    message=str(e)
                )
            )
    
    async def process_user_response(self, session_id: str, user_response: str) -> WorkflowResponse:
        logger.info(f"Processing user response for session {session_id}")
        try:
            session = await self._load_session(session_id)
            if not session:
                return WorkflowResponse(
                    success=False,
                    message="Sorry, I couldn't find your appointment booking session. Let's start over.",
                    error_details=AppointmentError(
                        error_type="SESSION_NOT_FOUND",
                        message="Session not found in database"
                    )
                )
            session.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "type": "user_response",
                "message": user_response
            })
            await self._extract_and_update_information(session, user_response)
            session.updated_at = datetime.now()
            await self._save_session(session)
            return await self._get_next_workflow_step(session)
        except Exception as e:
            logger.error(f"Error processing user response: {e}")
            return WorkflowResponse(
                success=False,
                message="Sorry, there was an issue processing your response. Could you please try again?",
                error_details=AppointmentError(
                    error_type="RESPONSE_PROCESSING_ERROR",
                    message=str(e)
                )
            )
    
    async def generate_confirmation_ui(self, session: AppointmentSession) -> ConfirmationUI:
        appointment = session.collected_data
        formatted_date = appointment.date.strftime("%A, %B %d, %Y at %I:%M %p")
        attendees_text = ", ".join(appointment.attendee_emails) if appointment.attendee_emails else "No additional attendees"
        appointment_card = {
            "type": "appointment_confirmation",
            "title": "📅 Appointment Confirmation",
            "details": {
                "meeting_title": appointment.title,
                "location": f"📍 {appointment.location}",
                "datetime": f"🕐 {formatted_date}",
                "duration": f"⏱️ {appointment.duration_minutes} minutes",
                "attendees": f"👥 {attendees_text}",
                "description": appointment.description or "No additional details"
            }
        }
        action_buttons = [
            {"id": "confirm_appointment", "text": "✅ Confirm Appointment", "type": "primary", "action": "confirm"},
            {"id": "cancel_appointment", "text": "❌ Cancel", "type": "secondary", "action": "cancel"}
        ]
        styling = {
            "card": {"background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", "borderRadius": "12px", "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)", "padding": "24px", "color": "white"},
            "buttons": {
                "primary": {"background": "#10B981", "color": "white", "border": "none", "borderRadius": "8px", "padding": "12px 24px", "fontWeight": "600"},
                "secondary": {"background": "#EF4444", "color": "white", "border": "none", "borderRadius": "8px", "padding": "12px 24px", "fontWeight": "600"}
            }
        }
        animations = {
            "entrance": {"type": "slideUp", "duration": "300ms", "easing": "ease-out"},
            "buttonHover": {"type": "scale", "scale": "1.05", "duration": "200ms"}
        }
        return ConfirmationUI(appointment_card=appointment_card, action_buttons=action_buttons, styling=styling, animations=animations)
    
    async def confirm_appointment(self, session_id: str) -> WorkflowResponse:
        logger.info(f"Confirming appointment for session {session_id}")
        try:
            session = await self._load_session(session_id)
            if not session:
                return WorkflowResponse(success=False, message="Appointment session not found.", error_details=AppointmentError(error_type="SESSION_NOT_FOUND", message="Session not found"))
            session.status = AppointmentStatus.CONFIRMED
            session.updated_at = datetime.now()
            appointment = session.collected_data
            await self._save_session(session)
            formatted_date = appointment.date.strftime("%A, %B %d, %Y at %I:%M %p")
            success_message = f"""🎉 **Appointment Confirmed!**

Your appointment has been successfully scheduled:

📋 **{appointment.title}**
📍 **Location:** {appointment.location}
🕐 **Date & Time:** {formatted_date}
⏱️ **Duration:** {appointment.duration_minutes} minutes

You will receive a calendar invitation shortly with all the details and a Google Meet link for the meeting.""".strip()
            return WorkflowResponse(success=True, message=success_message, session_id=session_id, step_name="appointment_confirmed", appointment_data=appointment)
        except Exception as e:
            logger.error(f"Error confirming appointment: {e}")
            return WorkflowResponse(success=False, message="Sorry, there was an issue confirming your appointment. Please try again.", error_details=AppointmentError(error_type="CONFIRMATION_ERROR", message=str(e)))
    
    async def cancel_appointment(self, session_id: str) -> WorkflowResponse:
        logger.info(f"Cancelling appointment for session {session_id}")
        try:
            session = await self._load_session(session_id)
            if session:
                session.status = AppointmentStatus.CANCELLED
                session.updated_at = datetime.now()
                await self._save_session(session)
            return WorkflowResponse(success=True, message="No problem! Your appointment booking has been cancelled. Feel free to ask me anything else or start a new appointment booking whenever you're ready.", session_id=session_id, step_name="appointment_cancelled")
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            return WorkflowResponse(success=True, message="Your appointment booking has been cancelled. Feel free to ask me anything else!", session_id=session_id, step_name="appointment_cancelled")
    
    async def _get_next_workflow_step(self, session: AppointmentSession) -> WorkflowResponse:
        if session.status == AppointmentStatus.CONFIRMING:
            if hasattr(session.collected_data, 'confirmation_response'):
                if session.collected_data.confirmation_response == "confirmed":
                    logger.info(f"Processing confirmation response")
                    return await self._confirm_appointment_internal(session)
                elif session.collected_data.confirmation_response == "cancelled":
                    logger.info(f"Processing cancellation response")
                    return await self._cancel_appointment_internal(session)
        missing_fields = self._check_missing_fields(session.collected_data)
        session.missing_fields = missing_fields
        if missing_fields:
            session.status = AppointmentStatus.COLLECTING_INFO
            question = await self._generate_information_question(session, missing_fields[0])
            return WorkflowResponse(success=True, message=question, session_id=session.session_id, step_name="collecting_information", next_step=missing_fields[0])
        else:
            session.status = AppointmentStatus.CONFIRMING
            confirmation_ui = await self.generate_confirmation_ui(session)
            confirmation_message = f"""Perfect! I have all the details for your appointment. Please review and confirm:

**{session.collected_data.title}**
📍 **Location:** {session.collected_data.location}
🕐 **Date & Time:** {session.collected_data.date.strftime("%A, %B %d, %Y at %I:%M %p")}
⏱️ **Duration:** {session.collected_data.duration_minutes} minutes

Would you like me to confirm this appointment?""".strip()
            return WorkflowResponse(success=True, message=confirmation_message, session_id=session.session_id, step_name="awaiting_confirmation", ui_components=confirmation_ui)
    
    def _apply_extracted_details(self, appointment_data: AppointmentData, extracted_details: Dict[str, Any]):
        if 'location' in extracted_details:
            appointment_data.location = extracted_details['location']
        if 'title' in extracted_details:
            appointment_data.title = extracted_details['title']
        if 'email' in extracted_details:
            emails = extracted_details['email']
            if isinstance(emails, list):
                appointment_data.attendee_emails.extend(emails)
            else:
                appointment_data.attendee_emails.append(emails)
        if 'date' in extracted_details and 'time' in extracted_details:
            appointment_data.date = self._parse_datetime(extracted_details['date'], extracted_details.get('time', '2:00 PM'))
        elif 'date' in extracted_details:
            appointment_data.date = self._parse_datetime(extracted_details['date'], '2:00 PM')
        elif 'time' in extracted_details:
            tomorrow = datetime.now() + timedelta(days=1)
            appointment_data.date = self._parse_datetime('tomorrow', extracted_details['time'])
    
    def _parse_datetime(self, date_str: str, time_str: str) -> datetime:
        now = datetime.now()
        if 'tomorrow' in date_str.lower():
            date_base = now + timedelta(days=1)
        elif 'today' in date_str.lower():
            date_base = now
        else:
            date_base = now + timedelta(days=1)
        if 'pm' in time_str.lower():
            hour = 14
        else:
            hour = 10
        return date_base.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    def _check_missing_fields(self, appointment_data: AppointmentData) -> List[str]:
        missing = []
        if not appointment_data.location or appointment_data.location.strip() == "":
            missing.append("location")
        if appointment_data.date <= datetime.now():
            missing.append("date_time")
        return missing
    
    async def _generate_information_question(self, session: AppointmentSession, missing_field: str) -> str:
        question_prompts = {
            "location": "Where would you like to have this meeting? You can specify an address, office location, or if it should be a virtual meeting.",
            "date_time": "When would you like to schedule this meeting? Please let me know your preferred date and time.",
            "attendees": "Who else should I invite to this meeting? Please provide their email addresses."
        }
        return question_prompts.get(missing_field, f"I need some additional information about your {missing_field}. Could you please provide that?")
    
    async def _extract_and_update_information(self, session: AppointmentSession, user_response: str):
        logger.info(f"Processing user response: '{user_response}' for session {session.session_id}")
        if session.status == AppointmentStatus.CONFIRMING:
            response_lower = user_response.lower().strip()
            if any(keyword in response_lower for keyword in ['yes', 'confirm', 'ok', 'okay', 'sure', 'correct', 'right', 'approve', 'proceed', 'go ahead']):
                session.collected_data.confirmation_response = "confirmed"
                return
            if any(keyword in response_lower for keyword in ['no', 'cancel', 'stop', 'abort', 'never mind', 'not now']):
                session.collected_data.confirmation_response = "cancelled"
                return
        intent_result = await apointment_intent_detection_service.detect_appointment_intent(user_response)
        self._apply_extracted_details(session.collected_data, intent_result.extracted_details)
        if (session.status == AppointmentStatus.COLLECTING_INFO and (not session.collected_data.location or session.collected_data.location.strip() == "")):
            if (any(word in user_response.lower() for word in ['office', 'building', 'room', 'address', 'virtual', 'zoom', 'meet', 'street', 'st', 'avenue', 'ave', 'road', 'rd', 'boulevard', 'blvd', 'drive', 'dr']) or self._looks_like_address(user_response)) and not any(phrase in user_response.lower() for phrase in ['schedule', 'appointment', 'meeting', 'book', 'arrange', 'set up']):
                session.collected_data.location = user_response.strip()
        if any(word in user_response.lower() for word in ['tomorrow', 'today', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday']):
            session.collected_data.date = self._parse_datetime(user_response, '2:00 PM')
    
    def _looks_like_address(self, text: str) -> bool:
        return bool(re.search(r'\d+\s+\w+\s+(street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|place|pl|lane|ln|way|court|ct)', text.lower().strip()) or re.match(r'^\d+\s+\w+.*', text.strip()))
    
    async def _save_session(self, session: AppointmentSession):
        try:
            db = get_database()
            collection = db["appointment_sessions"]
            session_dict = {"_id": session.session_id, "user_id": session.user_id, "status": session.status.value, "collected_data": {"title": session.collected_data.title, "location": session.collected_data.location, "date": session.collected_data.date.isoformat(), "duration_minutes": session.collected_data.duration_minutes, "attendee_emails": session.collected_data.attendee_emails, "description": session.collected_data.description, "meet_link": session.collected_data.meet_link, "calendar_event_id": session.collected_data.calendar_event_id, "organizer_email": session.collected_data.organizer_email}, "missing_fields": session.missing_fields, "created_at": session.created_at.isoformat(), "updated_at": session.updated_at.isoformat(), "conversation_history": session.conversation_history}
            await collection.replace_one({"_id": session.session_id}, session_dict, upsert=True)
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            raise
    
    async def _load_session(self, session_id: str) -> Optional[AppointmentSession]:
        try:
            db = get_database()
            collection = db["appointment_sessions"]
            session_doc = await collection.find_one({"_id": session_id})
            if not session_doc:
                return None
            data_dict = session_doc["collected_data"]
            appointment_data = AppointmentData(title=data_dict["title"], location=data_dict["location"], date=datetime.fromisoformat(data_dict["date"]), duration_minutes=data_dict["duration_minutes"], attendee_emails=data_dict["attendee_emails"], description=data_dict.get("description"), meet_link=data_dict.get("meet_link"), calendar_event_id=data_dict.get("calendar_event_id"), organizer_email=data_dict.get("organizer_email"))
            return AppointmentSession(session_id=session_doc["_id"], user_id=session_doc["user_id"], status=AppointmentStatus(session_doc["status"]), collected_data=appointment_data, missing_fields=session_doc.get("missing_fields", []), created_at=datetime.fromisoformat(session_doc["created_at"]), updated_at=datetime.fromisoformat(session_doc["updated_at"]), conversation_history=session_doc.get("conversation_history", []))
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return None

    async def _confirm_appointment_internal(self, session: AppointmentSession) -> WorkflowResponse:
        session.status = AppointmentStatus.CONFIRMED
        session.updated_at = datetime.now()
        await self._save_session(session)
        appointment = session.collected_data
        formatted_date = appointment.date.strftime("%A, %B %d, %Y at %I:%M %p")
        success_message = f"""🎉 **Appointment Confirmed!**

Your appointment has been successfully scheduled:

📋 **{appointment.title}**
📍 **Location:** {appointment.location}
🕐 **Date & Time:** {formatted_date}
⏱️ **Duration:** {appointment.duration_minutes} minutes

You will receive a calendar invitation shortly with all the details and a Google Meet link for the meeting.""".strip()
        return WorkflowResponse(success=True, message=success_message, session_id=session.session_id, step_name="appointment_confirmed", appointment_data=appointment)

    async def _cancel_appointment_internal(self, session: AppointmentSession) -> WorkflowResponse:
        session.status = AppointmentStatus.CANCELLED
        session.updated_at = datetime.now()
        await self._save_session(session)
        return WorkflowResponse(success=True, message="No problem! Your appointment booking has been cancelled. Feel free to ask me anything else or start a new appointment booking whenever you're ready.", session_id=session.session_id, step_name="appointment_cancelled")

appointment_workflow_manager = AppointmentWorkflowManager()