import time
import base64
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google.cloud import speech
from google.cloud import texttospeech
from langchain_core.messages import HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from app.main import agent_graph
from langchain_core.runnables.history import RunnableWithMessageHistory
from app.core.session import get_session_history

router = APIRouter()

# --- Pydantic Models for API Contracts ---
class TranscribeRequest(BaseModel):
    audio_data: str  # Base64-encoded audio string

class TranscribeResponse(BaseModel):
    text: str
    stt_time: float

class SpeakRequest(BaseModel):
    text: str

class SpeakResponse(BaseModel):
    audio_data: str  # Base64-encoded audio string
    tts_time: float

# --- Agent Setup ---
agent_with_history = RunnableWithMessageHistory(
    agent_graph,
    get_session_history,
    input_messages_key="message",
    history_messages_key="history",
    output_messages_key="generation",
)

# --- API Endpoints ---

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """Transcribes base64-encoded audio using Google Cloud Speech-to-Text."""
    start_time = time.time()
    try:
        client = speech.SpeechClient()
        audio_bytes = base64.b64decode(request.audio_data)
        audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        response = client.recognize(config=config, audio=audio)
        if not response.results or not response.results[0].alternatives:
            raise HTTPException(status_code=400, detail="Could not transcribe audio.")
        transcript = response.results[0].alternatives[0].transcript
    except Exception as e:
        print(f"--- ERROR in /transcribe: {e} ---")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to transcribe audio: {e}")
    stt_time = time.time() - start_time
    return TranscribeResponse(text=transcript, stt_time=stt_time)

@router.post("/speak", response_model=SpeakResponse)
async def speak_text(request: SpeakRequest):
    """Synthesizes text into speech using Google Cloud Text-to-Speech."""
    start_time = time.time()
    try:
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=request.text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        audio_data = base64.b64encode(response.audio_content).decode('utf-8')
    except Exception as e:
        print(f"--- ERROR in /speak: {e} ---")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to synthesize speech: {e}")
    tts_time = time.time() - start_time
    return SpeakResponse(audio_data=audio_data, tts_time=tts_time)

# ------------------------------- VOICE CONVERSE -------------------------------

class ConverseRequest(BaseModel):
    session_id: str
    audio_data: str  # Base64-encoded user speech
    use_rag: bool = True
    use_web_search: bool = False

class ConverseResponse(BaseModel):
    audio_data: str      # Base64-encoded AI speech
    transcription: str   # Text from STT
    response_text: str   # AI text reply
    stt_time: float
    llm_time: float
    tts_time: float
    total_time: float

@router.post("/converse", response_model=ConverseResponse)
async def converse(request: ConverseRequest):
    """End-to-end voice conversation with persistent memory."""
    overall_start = time.time()

    # 1. Speech-to-Text
    stt_start = time.time()
    try:
        speech_client = speech.SpeechClient()
        audio_bytes = base64.b64decode(request.audio_data)
        audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        stt_response = speech_client.recognize(config=config, audio=audio)
        if not stt_response.results or not stt_response.results[0].alternatives:
            raise HTTPException(status_code=400, detail="Could not transcribe audio.")
        transcript = stt_response.results[0].alternatives[0].transcript
    except Exception as e:
        print(f"--- ERROR in STT stage: {e} ---")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")
    stt_time = time.time() - stt_start

    # 2. LLM / RAG with History
    llm_start = time.time()
    try:
        # Correctly structure the input for the agent
        input_data = {
            "message": transcript,
            "session_id": request.session_id,
            "use_rag": request.use_rag,
            "use_web_search": request.use_web_search,
        }
        config = {"configurable": {"session_id": request.session_id}}
        
        print(f"--- DEBUG: Invoking agent with history with input: {input_data} and config: {config} ---")
        state = await agent_with_history.ainvoke(input_data, config=config)
        print(f"--- DEBUG: Agent returned state: {state} ---")
        
        response_text = state["messages"][-1].content
    except Exception as e:
        print(f"--- ERROR in LLM stage: {e} ---")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {e}")
    llm_time = time.time() - llm_start

    # 3. Text-to-Speech
    tts_start = time.time()
    try:
        tts_client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=response_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        tts_response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        ai_audio_b64 = base64.b64encode(tts_response.audio_content).decode("utf-8")
    except Exception as e:
        print(f"--- ERROR in TTS stage: {e} ---")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")
    tts_time = time.time() - tts_start

    total_time = time.time() - overall_start

    return ConverseResponse(
        audio_data=ai_audio_b64,
        transcription=transcript,
        response_text=response_text,
        stt_time=stt_time,
        llm_time=llm_time,
        tts_time=tts_time,
        total_time=total_time,
    )
