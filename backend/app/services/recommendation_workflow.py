import logging
import re
import json
from typing import Dict, List, Any, Optional
from llama_index.core.llms import ChatMessage
from llama_index.core import Settings
import app.rag as rag_module
from app.models.crm_models import RecommendationIntent, RecommendationResult, WorkflowSession, WorkflowStep, ConversationState, UserContext
from app.services.database_service import get_database

logger = logging.getLogger(__name__)

class IntentDetectionService:
    RECOMMENDATION_TRIGGERS = [
        r'\b(?:suggest|recommend|find|show)\s+(?:me\s+)?(?:a\s+|some\s+)?(?:property|properties|apartment|apartments|listing|listings|place|places)\b',
        r'\b(?:any|got any)\s+(?:good\s+)?(?:property|properties|apartment|apartments|listing|listings|place|places)\s+(?:for\s+me|available)\b',
        r'\b(?:what\s+do\s+you\s+have|what\s+properties)\b',
        r'\b(?:looking\s+for|searching\s+for)\s+(?:a\s+|some\s+)?(?:property|apartment|place)\b',
        r'\b(?:help\s+me\s+find|can\s+you\s+find)\s+(?:a\s+|some\s+)?(?:property|apartment|place)\b',
        r'\b(?:any\s+)?(?:listings|properties|apartments|places)\s+(?:for\s+me|you\s+suggest)\b',
        r'\b(?:what\s+would\s+you\s+recommend|what\s+do\s+you\s+recommend)\b',
        r'\b(?:show\s+me\s+your|what\s+are\s+your)\s+(?:best\s+)?(?:options|listings|properties)\b',
        r'\b(?:do\s+you\s+have\s+any|are\s+there\s+any)\s+(?:good\s+)?(?:properties|apartments|listings)\b',
        r'\b(?:what\s+kinds?\s+of|what\s+types?\s+of)\s+(?:properties|apartments)\s+(?:do\s+you\s+have|are\s+available)\b',
    ]
    
    PREFERENCE_PATTERNS = {
        'budget': [
            r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:to|[-–])\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(?:budget|price|rent)\s+(?:of\s+|around\s+|up\s+to\s+)?\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'under\s+\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'max\s+\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        ],
        'location': [
            r'\b(?:in|near|around|close\s+to)\s+([A-Za-z\s]+(?:street|st|avenue|ave|road|rd|blvd|boulevard|drive|dr|lane|ln|court|ct|place|pl)?)\b',
            r'\b(?:downtown|midtown|uptown|brooklyn|manhattan|queens|bronx|staten\s+island)\b',
            r'\b\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|blvd|boulevard|drive|dr|lane|ln|court|ct|place|pl)\b',
        ],
        'size': [
            r'(\d+(?:,\d{3})*)\s*(?:sq\s*ft|square\s+feet|sf)\b',
            r'(\d+)\s*(?:bedroom|bed|br)\b',
            r'(\d+)\s*(?:bathroom|bath|ba)\b',
        ],
        'features': [
            r'\b(kitchen|chef\s+kitchen|modern\s+kitchen|updated\s+kitchen)\b',
            r'\b(balcony|terrace|patio|outdoor\s+space)\b',
            r'\b(parking|garage|parking\s+spot)\b',
            r'\b(laundry|washer|dryer|in-unit\s+laundry)\b',
            r'\b(gym|fitness|fitness\s+center|workout\s+room)\b',
            r'\b(pool|swimming\s+pool)\b',
            r'\b(elevator|doorman|concierge)\b',
            r'\b(pet\s+friendly|pets\s+allowed|dog\s+friendly)\b',
        ]
    }
    
    def __init__(self):
        self.compiled_triggers = [re.compile(pattern, re.IGNORECASE) for pattern in self.RECOMMENDATION_TRIGGERS]
        self.compiled_preferences = {
            category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for category, patterns in self.PREFERENCE_PATTERNS.items()
        }
    
    async def detect_recommendation_intent(self, message: str) -> RecommendationIntent:
        logger.info(f"Analyzing message for recommendation intent: '{message[:100]}...' ")
        pattern_result = self._detect_patterns(message)
        llm_result = await self._llm_based_detection(message)
        initial_preferences = self.extract_initial_preferences(message)
        final_intent = self._combine_detection_results(pattern_result, llm_result, initial_preferences)
        logger.info(f"Intent detection result: is_recommendation={final_intent.is_recommendation_request}, confidence={final_intent.confidence:.2f}")
        return final_intent
    
    def _detect_patterns(self, message: str) -> Dict[str, Any]:
        matched_triggers = []
        for i, pattern in enumerate(self.compiled_triggers):
            if pattern.search(message):
                matched_triggers.append(self.RECOMMENDATION_TRIGGERS[i])
        return {'is_recommendation': len(matched_triggers) > 0, 'confidence': min(0.8, len(matched_triggers) * 0.3), 'triggers': matched_triggers}
    
    async def _llm_based_detection(self, message: str) -> Dict[str, Any]:
        detection_prompt = f"""Analyze this user message to determine if they are requesting property recommendations. Respond with ONLY a JSON object: {{'is_recommendation_request': true/false, 'confidence': 0.0-1.0, 'reasoning': 'brief explanation'}}"""
        try:
            response = await Settings.llm.achat([ChatMessage(role="user", content=detection_prompt)])
            response_content = response.message.content or '{}'
            logger.debug(f"LLM response for intent detection: {response_content}")
            if response_content.strip().startswith('{'):
                result = json.loads(response_content)
            else:
                json_match = re.search(r'\{[^}]*\}', response_content)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = {'is_recommendation_request': True, 'confidence': 0.8, 'reasoning': 'Pattern-based fallback'}
            return {'is_recommendation': result.get('is_recommendation_request', False), 'confidence': result.get('confidence', 0.0), 'reasoning': result.get('reasoning', '')}
        except Exception as e:
            logger.error(f"LLM-based intent detection failed: {e}")
            return {'is_recommendation': False, 'confidence': 0.0, 'reasoning': 'LLM detection failed'}
    
    def extract_initial_preferences(self, message: str) -> Dict[str, Any]:
        preferences = {}
        budget_info = self._extract_budget(message)
        if budget_info:
            preferences['budget'] = budget_info
        locations = self._extract_locations(message)
        if locations:
            preferences['preferred_locations'] = locations
        size_info = self._extract_size_requirements(message)
        if size_info:
            preferences.update(size_info)
        features = self._extract_features(message)
        if features:
            preferences['required_features'] = features
        logger.debug(f"Extracted preferences: {preferences}")
        return preferences
    
    def _extract_budget(self, message: str) -> Optional[Dict[str, Any]]:
        for pattern in self.compiled_preferences['budget']:
            match = pattern.search(message)
            if match:
                if len(match.groups()) >= 2:
                    min_budget = int(match.group(1).replace(',', ''))
                    max_budget = int(match.group(2).replace(',', ''))
                    return {'min': min_budget, 'max': max_budget, 'type': 'range'}
                else:
                    value = int(match.group(1).replace(',', ''))
                    if 'under' in match.group(0).lower() or 'max' in match.group(0).lower():
                        return {'max': value, 'type': 'max'}
                    else:
                        return {'target': value, 'type': 'target'}
        return None
    
    def _extract_locations(self, message: str) -> List[str]:
        locations = []
        for pattern in self.compiled_preferences['location']:
            matches = pattern.findall(message)
            locations.extend([match.strip() for match in matches if match.strip()])
        return list(set(locations))
    
    def _extract_size_requirements(self, message: str) -> Dict[str, Any]:
        size_info = {}
        for pattern in self.compiled_preferences['size']:
            match = pattern.search(message)
            if match:
                value = int(match.group(1).replace(',', ''))
                match_text = match.group(0).lower()
                if 'sq' in match_text or 'sf' in match_text:
                    size_info['square_feet'] = value
                elif 'bedroom' in match_text or 'bed' in match_text:
                    size_info['bedrooms'] = value
                elif 'bathroom' in match_text or 'bath' in match_text:
                    size_info['bathrooms'] = value
        return size_info
    
    def _extract_features(self, message: str) -> List[str]:
        features = []
        for pattern in self.compiled_preferences['features']:
            matches = pattern.findall(message)
            features.extend([match.strip() for match in matches if match.strip()])
        return list(set(features))
    
    def _combine_detection_results(self, pattern_result: Dict[str, Any], llm_result: Dict[str, Any], preferences: Dict[str, Any]) -> RecommendationIntent:
        is_recommendation = pattern_result['is_recommendation'] or llm_result['is_recommendation']
        pattern_confidence = pattern_result['confidence']
        llm_confidence = llm_result['confidence']
        combined_confidence = (pattern_confidence * 0.3) + (llm_confidence * 0.7)
        if preferences and is_recommendation:
            combined_confidence = min(1.0, combined_confidence + 0.1)
        return RecommendationIntent(is_recommendation_request=is_recommendation, confidence=combined_confidence, initial_preferences=preferences, trigger_phrases=pattern_result.get('triggers', []))

intent_detection_service = IntentDetectionService()

class RecommendationWorkflowManager:
    def __init__(self):
        pass
    
    async def start_recommendation_workflow(self, user_id: str, initial_message: str) -> WorkflowSession:
        session_id = str(uuid.uuid4())
        logger.info(f"Starting recommendation workflow {session_id} for user {user_id}")
        try:
            intent = await intent_detection_service.detect_recommendation_intent(initial_message)
            user_context = await user_context_analyzer.analyze_user_context(user_id)
            if intent.initial_preferences:
                user_context = await user_context_analyzer.merge_new_preferences(user_id, intent.initial_preferences)
            conversation_session = await conversation_state_manager.create_session(user_id, user_context)
            workflow_session = WorkflowSession(
                session_id=session_id,
                user_id=user_id,
                current_step="initiated",
                data={
                    "intent": intent.model_dump(),
                    "conversation_session_id": conversation_session.session_id,
                    "user_context": user_context.model_dump(),
                    "initial_message": initial_message
                }
            )
            await self._store_workflow_session(workflow_session)
            logger.info(f"Successfully started workflow {session_id} for user {user_id}")
            return workflow_session
        except Exception as e:
            logger.error(f"Error starting recommendation workflow: {e}")
            return WorkflowSession(session_id=session_id, user_id=user_id, current_step="failed", data={"error": str(e), "initial_message": initial_message})
    
    async def process_user_response(self, session_id: str, response: str) -> WorkflowStep:
        logger.info(f"Processing user response for workflow {session_id}")
        try:
            workflow_session = await self._get_workflow_session(session_id)
            if not workflow_session:
                return WorkflowStep(step_name="error", success=False, response_message="Session not found. Let's start over with your property preferences.", next_step=None)
            conversation_session_id = workflow_session.data.get("conversation_session_id")
            if not conversation_session_id:
                return WorkflowStep(step_name="error", success=False, response_message="Session error. Let's start fresh with your property search.", next_step=None)
            conversation_session = await conversation_state_manager.update_session(conversation_session_id, response)
            if await conversation_state_manager.is_conversation_complete(conversation_session):
                return await self._generate_recommendations_step(workflow_session)
            else:
                next_question = await conversation_state_manager.get_next_question(conversation_session)
                if next_question:
                    workflow_session.current_step = "gathering_preferences"
                    workflow_session.data["last_question"] = next_question
                    await self._store_workflow_session(workflow_session)
                    return WorkflowStep(step_name="clarifying_question", success=True, response_message=next_question, next_step="gathering_preferences", collected_data=conversation_session.collected_preferences)
                else:
                    return await self._generate_recommendations_step(workflow_session)
        except Exception as e:
            logger.error(f"Error processing user response: {e}")
            return WorkflowStep(step_name="error", success=False, response_message="I encountered an issue processing your response. Could you please try again?", next_step=None)
    
    async def _generate_recommendations_step(self, workflow_session: WorkflowSession) -> WorkflowStep:
        try:
            user_context = await user_context_analyzer.analyze_user_context(workflow_session.user_id)
            recommendations = await property_recommendation_engine.generate_recommendations(user_context, max_results=3)
            if recommendations:
                response_parts = ["Based on your preferences, here are my top recommendations:"]
                for i, rec in enumerate(recommendations, 1):
                    address = rec.property_data.get('property_address', 'Property')
                    rent = rec.property_data.get('monthly_rent')
                    rent_str = f"${rent:,}/month" if rent else "Contact for pricing"
                    response_parts.append(f"\n**{i}. {address}**")
                    response_parts.append(f"   • Rent: {rent_str}")
                    response_parts.append(f"   • {rec.explanation}")
                response_parts.append("\nWould you like more details about any of these properties or help with scheduling a viewing?")
                response_message = "\n".join(response_parts)
                workflow_session.current_step = "completed"
                workflow_session.data["recommendations"] = [rec.model_dump() for rec in recommendations]
                await self._store_workflow_session(workflow_session)
                return WorkflowStep(step_name="recommendations_generated", success=True, response_message=response_message, next_step=None, collected_data={"recommendations_count": len(recommendations)})
            else:
                return WorkflowStep(step_name="no_recommendations", success=False, response_message="I couldn't find any properties that match your criteria. Would you like to adjust your preferences or search requirements?", next_step=None)
        except Exception as e:
            logger.error(f"Error generating recommendations step: {e}")
            return WorkflowStep(step_name="error", success=False, response_message="I had trouble generating recommendations. Let me try a different approach.", next_step=None)
    
    async def _store_workflow_session(self, session: WorkflowSession) -> None:
        try:
            db = get_database()
            sessions_collection = db["workflow_sessions"]
            session_dict = session.model_dump()
            session_dict['_id'] = session.session_id
            await sessions_collection.replace_one({"_id": session.session_id}, session_dict, upsert=True)
        except Exception as e:
            logger.error(f"Error storing workflow session: {e}")
    
    async def _get_workflow_session(self, session_id: str) -> Optional[WorkflowSession]:
        try:
            db = get_database()
            sessions_collection = db["workflow_sessions"]
            session_data = await sessions_collection.find_one({"_id": session_id})
            if session_data:
                session_data.pop('_id', None)
                session_data['session_id'] = session_id
                return WorkflowSession(**session_data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving workflow session: {e}")
            return None

recommendation_workflow_manager = RecommendationWorkflowManager()
