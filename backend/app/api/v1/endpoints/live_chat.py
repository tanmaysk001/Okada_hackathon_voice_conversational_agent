import asyncio
import json
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.genai.types import LiveConnectConfig, SpeechConfig, VoiceConfig, PrebuiltVoiceConfig, Blob
from app.core.config import settings
from google import genai
from app.services import vector_store
from app.core.session_manager import get_session_history
from app.core.session import add_session_message
from dataclasses import dataclass, field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
import uuid

@dataclass
class LiveChatConfig:
    session_id: str
    is_rag_enabled: bool
    is_web_search_enabled: bool
    voice_name: str = "Puck"
    max_rag_chunks: int = 5
    response_modalities: List[str] = field(default_factory=lambda: ["AUDIO", "TEXT"])

@dataclass
class ConversationTurn:
    timestamp: datetime
    user_input: str
    user_audio_duration: Optional[float]
    ai_response: str
    ai_audio_duration: Optional[float]
    rag_context_used: Optional[str]
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class LiveChatResponse:
    type: Literal["audio", "text", "both"]
    audio_data: Optional[str]  # base64 encoded
    text_content: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RAGQueryResult:
    relevant_chunks: List[str]
    context_text: str
    relevance_scores: List[float]
    query_terms: List[str]

router = APIRouter()

client = genai.Client(api_key=settings.GOOGLE_API_KEY)
MODEL = "gemini-2.0-flash-live-001"




# --- [NEW] Helper to get RAG context ---
def get_rag_context_for_session(session_id: str) -> str:
    """
    Fetches all documents for a given session and concatenates their content
    to create a broad context for the entire voice conversation.
    """
    if not session_id:
        return "No session ID was provided."
        
    print(f"Fetching RAG context for session_id: {session_id}")
    # Retrieve more documents for a conversational context
    retriever = vector_store.get_retriever(session_id=session_id, search_kwargs={"k": 10})
    # Use a generic query to get a broad set of documents from the session
    all_docs = retriever.get_relevant_documents("all content about the uploaded documents") 
    
    if not all_docs:
        print(f"No documents found for session_id: {session_id}")
        return "No documents were found for this session."
        
    context = "\n\n---\n\n".join([doc.page_content for doc in all_docs])
    print(f"Found {len(all_docs)} document chunks for context.")
    return context


@router.websocket("/live-chat")
async def live_chat(websocket: WebSocket):
    print("[DEBUG] WebSocket endpoint called.")
    await websocket.accept()
    print("[DEBUG] WebSocket connection accepted.")

    try:
        initial_config_raw = await websocket.receive_text()
        print(f"[DEBUG] Received initial config raw: {initial_config_raw}")
        initial_config = json.loads(initial_config_raw).get("config", {})
        print(f"[DEBUG] Parsed initial config: {initial_config}")
        
        is_rag_enabled = initial_config.get("isRagEnabled", False)
        session_id = initial_config.get("sessionId")
        print(f"[DEBUG] is_rag_enabled: {is_rag_enabled}, session_id: {session_id}")
        
        system_instruction_text = "You are a friendly and helpful voice assistant. Keep your responses concise and conversational."
        history_messages = []

        if session_id:
            try:
                chat_history = get_session_history(session_id)
                print(f"[DEBUG] Got chat_history object for session_id: {session_id}")
                history_messages = await chat_history.aget_messages()
                print(f"[DEBUG] Loaded {len(history_messages)} messages from history for session {session_id}")
            except Exception as e:
                print(f"[DEBUG] Error loading session history: {e}")
                history_messages = []

        system_instruction_text = "You are a friendly and helpful voice assistant. Keep your responses concise and conversational."

        if is_rag_enabled:
            print("[DEBUG] Voice RAG mode enabled. Fetching context.")
            # [FIX] Stronger prompt to enforce RAG
            system_instruction_text = ("You are a specialized assistant. Your task is to answer questions based exclusively on the provided document context below. "
                                       "Do not use any external knowledge. If the answer is not found in the documents, you must state that you don't have the information. Be concise.")
            rag_context = get_rag_context_for_session(session_id)
            system_instruction_text += f"\n\n--- Provided Document Context ---\n{rag_context}\n--- End of Document Context ---"

        if history_messages:
            print(f"[DEBUG] Formatting {len(history_messages)} messages for history.")
            formatted_history = "\n\n--- Previous Conversation ---\n"
            for msg in history_messages:
                role = "User" if msg.type == "human" else "Assistant"
                formatted_history += f"{role}: {msg.content}\n"
            system_instruction_text = formatted_history + "\n\n" + system_instruction_text

        try:
            print(f"[DEBUG] Creating LiveConnectConfig with final system instruction length: {len(system_instruction_text)}")
            config = LiveConnectConfig(
                response_modalities=["AUDIO"],
                input_audio_transcription={},
                output_audio_transcription={}, # Request transcription of user audio
                speech_config=SpeechConfig(
                    voice_config=VoiceConfig(prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="Puck"))
                ),
                system_instruction=system_instruction_text,
                realtime_input_config={"speech_end_timeout_millis": 2000}  # <-- put your VAD config here
            )
            print("[DEBUG] LiveConnectConfig created successfully")
        except Exception as e:
            print(f"[DEBUG] Error creating LiveConnectConfig: {e}")
            raise

        try:
            print(f"[DEBUG] Attempting to connect to Gemini Live API with model: {MODEL}")
            async with client.aio.live.connect(model=MODEL, config=config) as session:
                print("[DEBUG] Gemini Live session started.")

                async def browser_to_gemini():
                    print("[DEBUG] browser_to_gemini started.")
                    while True:
                        try:
                            message = await websocket.receive_text()
                            data = json.loads(message)
                            
                            if "audio_chunk" in data:
                                # [DEBUG] audio_chunk found in data. Decoding base64... (message suppressed)
                                pcm_data = base64.b64decode(data["audio_chunk"])
                                await session.send_realtime_input(
                                    audio=Blob(data=pcm_data, mime_type="audio/pcm;rate=16000")
                                )
                                # [DEBUG] Sent realtime audio input to Gemini. (message suppressed)
                            if "text_input" in data:
                                print(f"[DEBUG] text_input found: {data['text_input']}")
                                await session.send_text_input(data["text_input"])
                                print("[DEBUG] Sent text input to Gemini.")

                        except WebSocketDisconnect:
                            print("[DEBUG] WebSocketDisconnect in browser_to_gemini.")
                            break
                        except Exception as e:
                            print(f"[DEBUG] Error in browser_to_gemini: {e}")
                            break

                async def gemini_to_browser():
                    print("[DEBUG] gemini_to_browser started.")
                    ai_response_text = ""
                    while True:
                        try:
                            async for response in session.receive():
                                print(f"[DEBUG] Received response from Gemini: {response}")
                                # Safely process server_content
                                if hasattr(response, 'server_content') and response.server_content:
                                    server_content = response.server_content
                                    # Handle input transcription (user's speech)
                                    if hasattr(server_content, 'input_transcription') and server_content.input_transcription:
                                        user_text = server_content.input_transcription.text if hasattr(server_content.input_transcription, 'text') else server_content.input_transcription
                                        if user_text:
                                            print(f"[DEBUG] User input transcription: {user_text}")
                                            await add_session_message(session_id, "user", user_text)
                                            await websocket.send_text(json.dumps({"user_transcript": user_text}))
                                            print("[DEBUG] Sent user_transcript to browser and saved to session.")
                                    # Handle output transcription (AI's speech)
                                    if hasattr(server_content, 'output_transcription') and server_content.output_transcription:
                                        ai_text = server_content.output_transcription.text if hasattr(server_content.output_transcription, 'text') else server_content.output_transcription
                                        if ai_text:
                                            print(f"[DEBUG] AI output transcription: {ai_text}")
                                            await websocket.send_text(json.dumps({"text_response": ai_text}))
                                            print("[DEBUG] Sent text_response to browser.")
                                    # Handle audio and model turn
                                    if hasattr(server_content, 'model_turn') and server_content.model_turn:
                                        for part in server_content.model_turn.parts:
                                            if part.inline_data:
                                                print("[DEBUG] Inline audio data found in Gemini response.")
                                                audio_data = part.inline_data.data
                                                base64_audio = base64.b64encode(audio_data).decode('utf-8')
                                                await websocket.send_text(json.dumps({"audio_chunk": base64_audio}))
                                                print("[DEBUG] Sent audio_chunk to browser.")
                                            if part.text:
                                                print(f"[DEBUG] Text part found in Gemini response: {part.text}")
                                                ai_response_text += part.text
                                                await websocket.send_text(json.dumps({"text_response": part.text}))
                                                print("[DEBUG] Sent text_response to browser.")
                                    # Save AI response if final
                                    if ai_response_text and hasattr(server_content, 'is_final') and server_content.is_final:
                                        print(f"[DEBUG] Final AI response: {ai_response_text}")
                                        await add_session_message(session_id, "assistant", ai_response_text)
                                        ai_response_text = ""
                                        print("[DEBUG] Saved AI response to session.")
                        except Exception as e:
                            print(f"[DEBUG] Error in gemini_to_browser: {e}")
                            break
                
                await asyncio.gather(browser_to_gemini(), gemini_to_browser())
        except Exception as e:
            print(f"[DEBUG] Error connecting to Gemini Live API: {e}")
            raise

    except WebSocketDisconnect:
        print("[DEBUG] WebSocket connection closed by client.")
    except Exception as e:
        print(f"[DEBUG] An error occurred: {e}")
    finally:
        print("[DEBUG] Live chat session ended.")