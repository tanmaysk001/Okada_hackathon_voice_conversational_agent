import logging
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from llama_index.core.schema import NodeWithScore
from llama_index.core.llms import ChatMessage
from llama_index.core import Settings

logger = logging.getLogger(__name__)

@dataclass
class ContextValidationResult:
    is_valid: bool
    context_summary: str
    property_count: int
    has_specific_property: bool
    specific_property_address: Optional[str]
    validation_issues: List[str]
    confidence_score: float

@dataclass
class ResponseQualityResult:
    is_valid: bool
    uses_only_context: bool
    contains_hallucination: bool
    quality_issues: List[str]
    confidence_score: float

@dataclass
class StrictResponseResult:
    response_text: str
    context_validation: ContextValidationResult
    quality_validation: ResponseQualityResult
    generation_successful: bool
    fallback_used: bool
    metadata: Dict[str, Any]

class StrictResponseGenerator:
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".StrictResponseGenerator")
    
    async def generate_strict_response(
        self,
        user_query: str,
        retrieved_nodes: List[NodeWithScore],
        user_id: Optional[str] = None
    ) -> StrictResponseResult:
        self.logger.info(f"Starting strict response generation for user '{user_id}' with {len(retrieved_nodes)} nodes")
        
        context_validation = await self._validate_context(user_query, retrieved_nodes)
        
        if not context_validation.is_valid:
            return await self._generate_not_found_response(user_query, context_validation, user_id)
        
        try:
            response_text = await self._generate_response_from_context(
                user_query, retrieved_nodes, context_validation
            )
            
            quality_validation = await self._validate_response_quality(
                user_query, retrieved_nodes, response_text
            )
            
            return StrictResponseResult(
                response_text=response_text,
                context_validation=context_validation,
                quality_validation=quality_validation,
                generation_successful=True,
                fallback_used=False,
                metadata={
                    "user_id": user_id,
                    "nodes_used": len(retrieved_nodes),
                    "generation_method": "strict_context"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error during response generation for user '{user_id}': {e}")
            return await self._generate_error_response(user_query, context_validation, str(e), user_id)
    
    async def _validate_context(
        self,
        user_query: str,
        retrieved_nodes: List[NodeWithScore]
    ) -> ContextValidationResult:
        if not retrieved_nodes:
            return ContextValidationResult(
                is_valid=False,
                context_summary="No context available",
                property_count=0,
                has_specific_property=False,
                specific_property_address=None,
                validation_issues=["No retrieved nodes available"],
                confidence_score=0.0
            )
        
        property_count = len(retrieved_nodes)
        specific_property_address = self._extract_address_from_query(user_query)
        confidence_score = 0.8 if property_count > 0 else 0.0
        
        validation_issues = []
        if property_count == 0:
            validation_issues.append("No retrieved nodes available")
        
        is_valid = property_count > 0
        
        return ContextValidationResult(
            is_valid=is_valid,
            context_summary=f"Found {property_count} documents in context",
            property_count=property_count,
            has_specific_property=True,
            specific_property_address=specific_property_address,
            validation_issues=validation_issues,
            confidence_score=confidence_score
        )
    
    async def _generate_response_from_context(
        self,
        user_query: str,
        retrieved_nodes: List[NodeWithScore],
        context_validation: ContextValidationResult
    ) -> str:
        formatted_context = self._format_context_for_prompt(retrieved_nodes)
        strict_prompt = self._create_strict_prompt(user_query, formatted_context, context_validation)
        chat_messages = [ChatMessage(role="user", content=strict_prompt)]
        response_obj = await Settings.llm.achat(chat_messages)
        return response_obj.message.content or ""
    
    def _create_strict_prompt(
        self,
        user_query: str,
        formatted_context: str,
        context_validation: ContextValidationResult
    ) -> str:
        return f"""You are a helpful real estate assistant. Answer the user's question using only the property information provided below.

PROPERTY INFORMATION:
{formatted_context}

USER'S QUESTION: {user_query}

FORMATTING REQUIREMENTS:
- Use PLAIN TEXT only - NO markdown, NO asterisks, NO special formatting
- For lists, use simple numbered format: "1. Property Name: Details"
- For emphasis, use CAPITAL LETTERS instead of bold/italic
- Use clear line breaks and spacing for readability
- Make the response easy to read in a chat interface

CONTENT REQUIREMENTS:
- Use only the information provided above
- If you don't have specific information, say so clearly
- Be helpful and direct in your response
- Quote specific details from the property data when relevant

Your response:"""
    
    async def _validate_response_quality(
        self,
        user_query: str,
        retrieved_nodes: List[NodeWithScore],
        response_text: str
    ) -> ResponseQualityResult:
        if not response_text:
            return ResponseQualityResult(
                is_valid=False,
                uses_only_context=False,
                contains_hallucination=True,
                quality_issues=["Empty response generated"],
                confidence_score=0.0
            )
        
        quality_issues = []
        hallucination_indicators = [
            "i know that", "it's well known", "typically", "usually", "generally",
            "most properties", "standard practice", "common in the area"
        ]
        
        response_lower = response_text.lower()
        for indicator in hallucination_indicators:
            if indicator in response_lower:
                quality_issues.append(f"Response contains potential hallucination indicator: '{indicator}'")
        
        safe_responses = [
            "i don't have", "not available", "not in our database", 
            "according to the data", "based on the available information"
        ]
        
        is_safe_response = any(phrase in response_lower for phrase in safe_responses)
        is_valid = len(quality_issues) == 0 or is_safe_response
        confidence_score = 0.9 if is_safe_response else (0.7 if len(quality_issues) == 0 else 0.3)
        
        return ResponseQualityResult(
            is_valid=is_valid,
            uses_only_context=True,
            contains_hallucination=len(quality_issues) > 0 and not is_safe_response,
            quality_issues=quality_issues,
            confidence_score=confidence_score
        )
    
    def _format_context_for_prompt(self, retrieved_nodes: List[NodeWithScore]) -> str:
        if not retrieved_nodes:
            return "No property data available."
        
        formatted_context = "AVAILABLE PROPERTIES:\n\n"
        for i, node in enumerate(retrieved_nodes, 1):
            content = node.get_content()
            score = getattr(node, 'score', 0.0)
            formatted_context += f"Property {i} (Relevance: {score:.3f}):\n{content}\n\n"
        return formatted_context
    
    def _extract_address_from_query(self, query: str) -> Optional[str]:
        patterns = [
            r'(\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Pl|Place)\.?)',
            r'tell me about\s+([^?]+)',
            r'information about\s+([^?]+)',
            r'show me\s+([^?]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                address = match.group(1).strip()
                address = re.sub(r'^(the\s+)?', '', address, flags=re.IGNORECASE)
                address = re.sub(r'\s+', ' ', address)
                return address
        return None

strict_response_generator = StrictResponseGenerator()
