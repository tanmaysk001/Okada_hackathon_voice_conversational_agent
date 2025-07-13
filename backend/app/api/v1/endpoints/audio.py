import time
import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google.cloud import speech
from google.cloud import texttospeech

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

# --- API Endpoints ---

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """
    Accepts base64-encoded audio data, transcribes it using Google Cloud Speech-to-Text,
    and returns the transcribed text along with the processing time.
    """
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
        print(f"Error during transcription: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to transcribe audio: {e}")
    finally:
        end_time = time.time()
        stt_time = end_time - start_time

    return TranscribeResponse(text=transcript, stt_time=stt_time)


@router.post("/speak", response_model=SpeakResponse)
async def speak_text(request: SpeakRequest):
    """
    Accepts text, synthesizes it into speech using Google Cloud Text-to-Speech,
    and returns the base64-encoded audio data along with the processing time.
    """
    start_time = time.time()
    try:
        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=request.text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        audio_data = base64.b64encode(response.audio_content).decode('utf-8')

    except Exception as e:
        print(f"Error during speech synthesis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to synthesize speech: {e}")
    finally:
        end_time = time.time()
        tts_time = end_time - start_time

    return SpeakResponse(audio_data=audio_data, tts_time=tts_time)

# ------------------------------- VOICE CONVERSE -------------------------------
from langchain_core.messages import HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from app.agent.graph import create_agent_graph
from app.core.session import get_session_history

# Create agent executor (shared)
_agent_graph = create_agent_graph()
_agent_executor = RunnableWithMessageHistory(
    _agent_graph,
    get_session_history,
    input_messages_key="input",
    history_messages_key="messages",
)

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
    """End-to-end voice conversation: speech-to-text ➜ LLM (RAG) ➜ text-to-speech."""
    overall_start = time.time()

    # -------------------- Speech-to-Text --------------------
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
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")
    stt_time = time.time() - stt_start

    # -------------------- LLM / RAG --------------------
    llm_start = time.time()
    inputs = {"input": [HumanMessage(content=transcript)]}
    config = {
        "configurable": {
            "session_id": request.session_id,
            "use_rag": request.use_rag,
            "use_web_search": request.use_web_search,
        }
    }
    try:
        state = await _agent_executor.ainvoke(inputs, config=config)
        response_text = state["messages"][-1].content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM processing failed: {e}")
    llm_time = time.time() - llm_start

    # -------------------- Text-to-Speech --------------------
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
