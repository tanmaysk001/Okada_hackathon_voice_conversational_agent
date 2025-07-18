import logging
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from app.models.crm_models import MessageType, MessageClassification, ProcessingStrategy, ConversationalContext

logger = logging.getLogger(__name__)

class FastMessageClassifier:
    GREETING_PATTERNS = [
        r'\b(hi|hello|hey|hiya|greetings|good\s+(morning|afternoon|evening|day))\b',
        r'\b(what\'s\s+up|how\s+(are\s+you|ya\s+doing)|how\s+do\s+you\s+do)\b',
        r'\b(nice\s+to\s+meet\s+you|pleased\s+to\s+meet\s+you)\b',
        r'^\s*(hi|hello|hey)\s*[!.,]*\s*$',
        r'\b(howdy|salutations|aloha)\b'
    ]
    
    THANK_YOU_PATTERNS = [
        r'\b(thank\s+you|thanks|thx|ty|appreciate|grateful)\b',
        r'\b(cheers|much\s+appreciated|awesome|perfect|great)\b',
        r'\b(that\'s\s+helpful|very\s+helpful|exactly\s+what\s+i\s+needed)\b',
        r'\b(excellent|fantastic|wonderful|amazing)\s+(help|service|response)\b'
    ]
    
    HELP_PATTERNS = [
        r'\b(help|assist|support|guide|explain|how\s+do\s+i)\b',
        r'\b(can\s+you\s+help|need\s+assistance|show\s+me\s+how)\b',
        r'\b(what\s+can\s+you\s+do|what\s+are\s+your\s+capabilities)\b',
        r'\b(how\s+does\s+this\s+work|getting\s+started)\b'
    ]
    
    PROPERTY_SEARCH_PATTERNS = [
        r'\b(find|search|look|show)\s+(me\s+)?(properties|apartments|listings|places)\b',
        r'\b(property|apartment|house|listing|rental)\s+(at|on|in|near)\b',
        r'\b(rent|lease|available|for\s+rent|to\s+rent)\b',
        r'\b\d+\s+(bedroom|bed|br)\b',
        r'\$\d+(\,\d+)*(\.\d+)?\s*(per\s+month|monthly|rent)',
        r'\b(square\s+feet|sq\s*ft|sf)\b',
        r'\b\d+\s+[NSEW]?\s*\w+\s+(st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive)\b'
    ]
    
    APPOINTMENT_PATTERNS = [
        r'\b(book|schedule|set\s+up|arrange|make)\s+(an?\s+)?(appointment|meeting|call)\b',
        r'\b(can\s+we\s+meet|let\'s\s+meet|available|free)\b',
        r'\b(calendar|schedule|appointment|meeting)\b'
    ]
    
    CONVERSATIONAL_PATTERNS = [
        r'\b(how\s+are\s+you|what\'s\s+new|how\'s\s+it\s+going)\b',
        r'\b(nice\s+weather|good\s+day|beautiful\s+day)\b',
        r'\b(just\s+chatting|just\s+saying\s+hi|checking\s+in)\b',
        r'\b(have\s+a\s+good\s+day|take\s+care|bye|goodbye)\b'
    ]

    MAINTENANCE_PATTERNS = [
        r'\b(fix|repair|broken|leaking|issue|problem)\b',
        r'\b(maintenance|plumbing|electricity|heating|ac|not working)\b',
        r'\b(send|schedule)\s+(a\s+)?(technician|handyman|plumber|electrician)\b'
    ]
    
    def __init__(self):
        self.compiled_greetings = [re.compile(pattern, re.IGNORECASE) for pattern in self.GREETING_PATTERNS]
        self.compiled_thanks = [re.compile(pattern, re.IGNORECASE) for pattern in self.THANK_YOU_PATTERNS]
        self.compiled_help = [re.compile(pattern, re.IGNORECASE) for pattern in self.HELP_PATTERNS]
        self.compiled_property = [re.compile(pattern, re.IGNORECASE) for pattern in self.PROPERTY_SEARCH_PATTERNS]
        self.compiled_appointment = [re.compile(pattern, re.IGNORECASE) for pattern in self.APPOINTMENT_PATTERNS]
        self.compiled_conversational = [re.compile(pattern, re.IGNORECASE) for pattern in self.CONVERSATIONAL_PATTERNS]
        self.compiled_maintenance = [re.compile(pattern, re.IGNORECASE) for pattern in self.MAINTENANCE_PATTERNS]
        self.classification_times = []
    
    def classify_message(self, message: str, user_context: Optional[ConversationalContext] = None) -> MessageClassification:
        start_time = time.time()
        try:
            normalized_message = self._normalize_message(message)

            # ** NEW LOGIC HERE **
            # Check for maintenance intent first, as it's very specific
            if any(p.search(normalized_message) for p in self.compiled_maintenance):
                return MessageClassification(
                    message_type=MessageType.APPOINTMENT_REQUEST,
                    confidence=0.9,
                    processing_strategy=ProcessingStrategy.MAINTENANCE_WORKFLOW, # Route to our new workflow
                    estimated_response_time=3000.0,
                    requires_index=False,
                    reasoning="Maintenance keyword detected"
                )

            classification_results = self._run_all_classifications(normalized_message)
            best_classification = self._select_best_classification(classification_results, user_context)
            duration_ms = (time.time() - start_time) * 1000
            self.classification_times.append(duration_ms)
            logger.debug(f"Fast classification completed in {duration_ms:.2f}ms: {best_classification.message_type} (confidence: {best_classification.confidence:.2f})")
            return best_classification
        except Exception as e:
            logger.error(f"Error in fast message classification: {e}")
            return MessageClassification(
                message_type=MessageType.UNKNOWN,
                confidence=0.0,
                processing_strategy=ProcessingStrategy.FALLBACK_RESPONSE,
                estimated_response_time=5000.0,
                requires_index=False,
                reasoning="Classification error - using fallback"
            )
    
    def _normalize_message(self, message: str) -> str:
        if not message:
            return ""
        normalized = message.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[!.?]{2,}', '.', normalized)
        return normalized
    
    def _run_all_classifications(self, normalized_message: str) -> List[Tuple[MessageType, float, str]]:
        results = []
        if any(p.search(normalized_message) for p in self.compiled_greetings):
            results.append((MessageType.GREETING, 0.9, "greeting patterns"))
        if any(p.search(normalized_message) for p in self.compiled_thanks):
            results.append((MessageType.THANK_YOU, 0.9, "thank you patterns"))
        if any(p.search(normalized_message) for p in self.compiled_help):
            results.append((MessageType.HELP_REQUEST, 0.8, "help request patterns"))
        if any(p.search(normalized_message) for p in self.compiled_appointment):
            results.append((MessageType.APPOINTMENT_REQUEST, 0.8, "appointment patterns"))
        
        property_confidence, property_reasoning = self._classify_property_search(normalized_message)
        if property_confidence > 0.3:
            if "direct query pattern" in property_reasoning or "top N pattern" in property_reasoning:
                results.append((MessageType.DIRECT_PROPERTY_QUERY, property_confidence, property_reasoning))
            else:
                results.append((MessageType.PROPERTY_SEARCH, property_confidence, property_reasoning))
        
        if any(p.search(normalized_message) for p in self.compiled_conversational):
            results.append((MessageType.CONVERSATIONAL, 0.6, "conversational patterns"))
        
        if not results or max(result[1] for result in results) < 0.4:
            results.append((MessageType.UNKNOWN, 0.3, "no clear patterns found"))
        
        return results
    
    def _select_best_classification(self, results: List[Tuple[MessageType, float, str]], user_context: Optional[ConversationalContext]) -> MessageClassification:
        if not results:
            return MessageClassification(
                message_type=MessageType.UNKNOWN,
                confidence=0.0,
                processing_strategy=ProcessingStrategy.FALLBACK_RESPONSE,
                estimated_response_time=5000.0,
                requires_index=False,
                reasoning="No patterns matched"
            )
        
        sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
        best_type, best_confidence, best_reasoning = sorted_results[0]
        
        strategy, estimated_time, requires_index = self._determine_processing_strategy(best_type, best_confidence)
        
        if user_context:
            strategy, estimated_time = self._apply_user_context(strategy, estimated_time, user_context)
        
        return MessageClassification(
            message_type=best_type,
            confidence=best_confidence,
            processing_strategy=strategy,
            estimated_response_time=estimated_time,
            requires_index=requires_index,
            reasoning=best_reasoning
        )
    
    def _determine_processing_strategy(self, message_type: MessageType, confidence: float) -> Tuple[ProcessingStrategy, float, bool]:
        if message_type in [MessageType.GREETING, MessageType.THANK_YOU, MessageType.CONVERSATIONAL]:
            return ProcessingStrategy.QUICK_RESPONSE, 1000.0, False
        elif message_type == MessageType.HELP_REQUEST:
            return ProcessingStrategy.QUICK_RESPONSE, 1500.0, False
        elif message_type == MessageType.DIRECT_PROPERTY_QUERY:
            return ProcessingStrategy.DIRECT_SEARCH, 3000.0, True
        elif message_type == MessageType.PROPERTY_SEARCH:
            if confidence > 0.8:
                return ProcessingStrategy.PROPERTY_WORKFLOW, 4000.0, True
            else:
                return ProcessingStrategy.FALLBACK_RESPONSE, 2000.0, False
        elif message_type == MessageType.APPOINTMENT_REQUEST:
            return ProcessingStrategy.APPOINTMENT_WORKFLOW, 3000.0, False
        else:
            return ProcessingStrategy.FALLBACK_RESPONSE, 5000.0, False
    
    def _apply_user_context(self, strategy: ProcessingStrategy, estimated_time: float, context: ConversationalContext) -> Tuple[ProcessingStrategy, float]:
        if context.previous_interactions > 5:
            estimated_time *= 0.9
        if context.user_preferences and strategy == ProcessingStrategy.PROPERTY_WORKFLOW:
            estimated_time *= 0.8
        return strategy, estimated_time

    def _classify_property_search(self, normalized_message: str) -> Tuple[float, str]:
        direct_query_patterns = [
            r'\b(?:top|best|cheapest|most expensive|lowest|highest|largest|smallest)\s+\d*\s*(?:property|properties|apartment|apartments|listing|listings)\b',
            r'\b(?:show|list|find)\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?(?:property|properties|apartment|apartments|listing|listings)\b',
            r'\b(?:properties|apartments|listings)\s+(?:under|over|above|below)\s+\$?\d+\b',
            r'\b(?:tell\s+me\s+about|what\s+is|info\s+about|details\s+about)\s+.+(?:street|st|avenue|ave|road|rd|drive|dr|place|pl)\b',
            r'\b\d+\s+\w+\s+(?:street|st|avenue|ave|road|rd|drive|dr|place|pl)\b',
            r'\b(?:search|filter)\s+(?:for\s+)?(?:property|properties|apartment|apartments)\b',
        ]
        
        recommendation_patterns = [
            r'\b(?:suggest|recommend)\s+(?:me\s+)?(?:a\s+|some\s+)?(?:property|properties|apartment|place)\b',
            r'\b(?:help\s+me\s+find)\s+(?:me\s+)?(?:a\s+|some\s+)?(?:property|properties|apartment|place)\b',
            r'\b(?:what\s+do\s+you\s+have|what\s+would\s+you\s+recommend)\b',
            r'\b(?:any\s+)?(?:good\s+)?(?:properties|apartments|places)\s+(?:for\s+me|you\s+suggest)\b',
            r'\b(?:looking\s+for|searching\s+for)\s+(?:a\s+)?(?:property|apartment|place)\s+(?:to\s+rent|for\s+rent)?\b',
            r'\b(?:i\s+need|i\s+want)\s+(?:a\s+|some\s+)?(?:property|apartment|place)\b'
        ]
        
        direct_query_score = 0.0
        recommendation_score = 0.0
        reasoning_parts = []
        
        for pattern in direct_query_patterns:
            if re.search(pattern, normalized_message):
                direct_query_score += 0.3
                reasoning_parts.append("direct query pattern")
        
        for pattern in recommendation_patterns:
            if re.search(pattern, normalized_message):
                recommendation_score += 0.4
                reasoning_parts.append("recommendation pattern")
        
        property_keywords = ['property', 'properties', 'apartment', 'apartments', 'listing', 'listings', 'rent', 'rental']
        action_keywords = ['show', 'list', 'find', 'search', 'tell me', 'what is', 'top', 'best', 'cheapest']
        suggest_keywords = ['suggest', 'recommend', 'help']
        
        property_count = sum(1 for keyword in property_keywords if keyword in normalized_message)
        action_count = sum(1 for keyword in action_keywords if keyword in normalized_message)
        suggest_count = sum(1 for keyword in suggest_keywords if keyword in normalized_message)
        
        if property_count > 0 and action_count > 0:
            direct_query_score += 0.4
            reasoning_parts.append("action+property keywords")
        
        if property_count > 0 and suggest_count > 0:
            recommendation_score += 0.5
            reasoning_parts.append("suggest+property keywords")
        
        if re.search(r'\b(?:top|cheapest|most expensive|lowest|highest|best)\s+\d+', normalized_message):
            direct_query_score += 0.5
            reasoning_parts.append("top N pattern")
        
        if re.search(r'\$\d+', normalized_message):
            direct_query_score += 0.2
            reasoning_parts.append("price mentioned")
        
        if re.search(r'\b\d+\s+(?:bedroom|bed|bath|sqft|sf)\b', normalized_message):
            direct_query_score += 0.2
            reasoning_parts.append("specific features")
        
        if re.search(r'\b\d+\s+\w+\s+(?:street|st|avenue|ave|road|rd)\b', normalized_message):
            direct_query_score += 0.6
            reasoning_parts.append("specific address")
        
        if direct_query_score > recommendation_score and direct_query_score > 0.5:
            confidence = min(0.9, direct_query_score)
            reasoning = f"Direct property query: {', '.join(reasoning_parts)}"
            return confidence, reasoning
        elif recommendation_score > 0.3:
            confidence = min(0.8, recommendation_score)
            reasoning = f"Recommendation request: {', '.join(reasoning_parts)}"
            return confidence, reasoning
        else:
            confidence = min(0.7, max(direct_query_score, recommendation_score))
            reasoning = f"General property search: {', '.join(reasoning_parts) if reasoning_parts else 'property keywords found'}"
            return confidence, reasoning