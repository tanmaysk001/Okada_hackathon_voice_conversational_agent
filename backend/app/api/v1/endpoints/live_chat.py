import asyncio
import json
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.genai.types import LiveConnectConfig, SpeechConfig, VoiceConfig, PrebuiltVoiceConfig, Blob
from app.core.config import settings
from google import genai
from app.services import vector_store 

router = APIRouter()

client = genai.Client(api_key=settings.GOOGLE_API_KEY)
MODEL = "gemini-2.0-flash-live-001" # Use the latest supported model

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
    await websocket.accept()
    print("WebSocket connection accepted.")

    try:
        # --- [MODIFIED] Wait for initial config from client ---
        initial_config_raw = await websocket.receive_text()
        initial_config = json.loads(initial_config_raw).get("config", {})
        
        is_rag_enabled = initial_config.get("isRagEnabled", False)
        session_id = initial_config.get("sessionId")
        
        system_prompt = "You are a friendly and helpful voice assistant. Keep your responses concise and conversational."

        if is_rag_enabled:
            print("Voice RAG mode enabled. Fetching context...")
            rag_context = get_rag_context_for_session(session_id)
            system_prompt = f"""You are an intelligent assistant. Your ONLY source of knowledge is the following set of documents provided by the user. Do not use your general knowledge.
            When asked a question, answer it directly using only information from these documents.
            If the answer is not in the documents, you MUST say 'The provided documents do not contain that information.'

            DOCUMENTS:
            ---
            {rag_context}
            ---
            
            Now, begin the conversation and answer the user's questions based on these documents.
            """
        else:
            print("Standard voice chat mode enabled.")
        # --- End Modified Section ---

        config = LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="Puck"))
            ),
            system_instruction=system_prompt, # <-- Use the dynamic prompt
        )

        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Gemini Live session started.")

            async def browser_to_gemini():
                while True:
                    try:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        
                        if "audio_chunk" in data:
                            pcm_data = base64.b64decode(data["audio_chunk"])
                            await session.send_realtime_input(
                                audio=Blob(data=pcm_data, mime_type="audio/pcm;rate=16000")
                            )
                    except WebSocketDisconnect:
                        break
                    except Exception as e:
                        print(f"Error in browser_to_gemini: {e}")
                        break

            async def gemini_to_browser():
                while True:
                    try:
                        async for response in session.receive():
                            if response.server_content and response.server_content.model_turn:
                                for part in response.server_content.model_turn.parts:
                                    if part.inline_data:
                                        audio_data = part.inline_data.data
                                        base64_audio = base64.b64encode(audio_data).decode('utf-8')
                                        await websocket.send_text(json.dumps({"audio_chunk": base64_audio}))
                    except Exception as e:
                        print(f"Error in gemini_to_browser: {e}")
                        break
            
            await asyncio.gather(browser_to_gemini(), gemini_to_browser())

    except WebSocketDisconnect:
        print("WebSocket connection closed by client.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Live chat session ended.")