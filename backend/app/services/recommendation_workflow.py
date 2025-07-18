# backend/app/services/recommendation_workflow.py

import logging
import re
import json
import uuid
from typing import Dict, List, Any, Optional
from llama_index.core.llms import ChatMessage
from llama_index.core import Settings
from app.models.crm_models import (
    RecommendationIntent, RecommendationResult, WorkflowSession, WorkflowStep,
    ConversationState, UserContext, PropertyRecommendation
)
from app.services.database_service import get_database
from app.services import vector_store, property_service # Correct import for RAG functionality

logger = logging.getLogger(__name__)

# --- Intent Detection Service (No changes needed here) ---
class IntentDetectionService:
    RECOMMENDATION_TRIGGERS = [
        r'\b(?:suggest|recommend|find|show)\s+(?:me\s+)?(?:a\s+|some\s+)?(?:property|properties|apartment|apartments|listing|listings|place|places)\b',
        r'\b(?:any|got any)\s+(?:good\s+)?(?:property|properties|apartment|apartments|listing|listings|place|places)\s+(?:for\s+me|available)\b',
        r'\b(?:what\s+do\s+you\s+have|what\s+properties)\b',
        r'\b(?:looking\s+for|searching\s+for)\s+(?:a\s+|some\s+)?(?:property|apartment|place)\b',
    ]
    
    def __init__(self):
        self.compiled_triggers = [re.compile(pattern, re.IGNORECASE) for pattern in self.RECOMMENDATION_TRIGGERS]

    async def detect_recommendation_intent(self, message: str) -> RecommendationIntent:
        is_request = any(pattern.search(message) for pattern in self.compiled_triggers)
        confidence = 0.9 if is_request else 0.1
        
        return RecommendationIntent(
            is_recommendation_request=is_request,
            confidence=confidence,
            initial_preferences={}, # Keep it simple for the fix
            trigger_phrases=[]
        )

intent_detection_service = IntentDetectionService()


# --- Recommendation Workflow Manager (Corrected and Implemented) ---
class RecommendationWorkflowManager:
    
    def __init__(self):
        self.db = None
        self.sessions_collection = None

    def init_db(self):
        """Initializes the database connection for the manager."""
        self.db = get_database()
        self.sessions_collection = self.db["recommendation_workflow_sessions"]

    async def _store_workflow_session(self, session: WorkflowSession):
        session_dict = session.model_dump(by_alias=True)
        await self.sessions_collection.replace_one(
            {"session_id": session.session_id}, session_dict, upsert=True
        )

    async def _get_workflow_session(self, session_id: str) -> Optional[WorkflowSession]:
        session_data = await self.sessions_collection.find_one({"session_id": session_id})
        return WorkflowSession(**session_data) if session_data else None

    async def start_recommendation_workflow(self, user_id: str, initial_message: str) -> WorkflowSession:
        session_id = str(uuid.uuid4())
        logger.info(f"Starting recommendation workflow {session_id} for user {user_id}")
        
        intent = await intent_detection_service.detect_recommendation_intent(initial_message)
        
        workflow_session = WorkflowSession(
            session_id=session_id,
            user_id=user_id,
            current_step="initiated",
            data={
                "intent": intent.model_dump(),
                "collected_preferences": {},
                "initial_message": initial_message,
                "history": [f"User: {initial_message}"]
            }
        )
        await self._store_workflow_session(workflow_session)
        logger.info(f"Successfully started workflow {session_id} for user {user_id}")
        return workflow_session

    async def get_next_step(self, session_id: str) -> Optional[WorkflowStep]:
        """Determines the next step, which is to generate recommendations."""
        workflow_session = await self._get_workflow_session(session_id)
        if not workflow_session:
            return None
            
        return await self._generate_recommendations_step(workflow_session)

    async def _generate_recommendations_step(self, workflow_session: WorkflowSession) -> WorkflowStep:
        """
        This is the final logic fix. It uses the resilient property_service and a very strict
        prompt to ensure the agent makes a recommendation and then immediately offers to book a viewing.
        """
        initial_query = workflow_session.data.get("initial_message", "find a property")
        logger.info(f"Generating recommendations from MongoDB for query: '{initial_query}'")

        try:
            # 1. Use our resilient service to get property data from MongoDB
            context_str = await property_service.get_properties_as_text(initial_query)

            if "No properties were found" in context_str:
                return WorkflowStep(
                    step_name="no_recommendations_found",
                    success=True,
                    response_message="I'm sorry, but I couldn't find any properties in our database right now. Please check back later.",
                    next_step="completed"
                )

            # 2. --- THE FINAL, DEMO-WINNING PROMPT ---
            prompt = f"""You are a professional and proactive real estate assistant for Okada. Your ONLY task is to help the user find a property from the internal database and book a viewing.

            **User's Request:** "{initial_query}"

            **Available Property Information from Okada's Database:**
            ---
            {context_str}
            ---

            **Your Instructions (Follow Exactly):**
            1.  Analyze the user's request and the available properties.
            2.  If the database results do not perfectly match the user's budget or location, acknowledge it briefly (e.g., "While I couldn't find an exact match for your budget, I did find a great option nearby...").
            3.  Select the SINGLE BEST property from the list to recommend to the user.
            4.  Present the details of this single best property in a friendly, concise summary.
            5.  Your response MUST end with a proactive question to book a viewing. For example: "Would you like me to schedule a viewing for this property for you?" or "If you're interested, I can book a viewing appointment right away."
            
            **DO NOT** say you cannot access the database. **DO NOT** ask for more preferences. Your goal is to recommend one property and book a viewing.
            """

            # 3. Call the LLM
            llm_response = await Settings.llm.achat([ChatMessage(role="user", content=prompt)])
            response_message = llm_response.message.content

            # 4. Update and save the session
            workflow_session.current_step = "completed"
            workflow_session.data["recommendations"] = response_message
            workflow_session.data["history"].append(f"Assistant: {response_message}")
            await self._store_workflow_session(workflow_session)

            return WorkflowStep(
                step_name="recommendations_generated",
                success=True,
                response_message=response_message,
                next_step="completed"
            )

        except Exception as e:
            logger.error(f"Error in _generate_recommendations_step for session {workflow_session.session_id}: {e}")
            return WorkflowStep(
                step_name="error",
                success=False,
                response_message="I'm sorry, I encountered an error while looking for recommendations. Please try again.",
                next_step="failed"
            )

# Singleton instance
recommendation_workflow_manager = RecommendationWorkflowManager()