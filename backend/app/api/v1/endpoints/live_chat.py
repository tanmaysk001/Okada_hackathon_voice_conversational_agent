import asyncio
import json
import base64
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.genai.types import LiveConnectConfig, SpeechConfig, VoiceConfig, PrebuiltVoiceConfig, Blob, FinalizeSpeechRequest
from app.core.config import settings
from google import genai
from app.agent.graph import create_agent_graph
from langchain_core.messages import HumanMessage 

router = APIRouter()

client = genai.Client(api_key=settings.GOOGLE_API_KEY)
MODEL = "gemini-2.0-flash-exp" # Use the latest supported model

@router.websocket("/live-chat")
async def live_chat(websocket: WebSocket):
    await websocket.accept()
    start_time = time.time()
    print("WebSocket connection accepted.")

    try:
        # --- [MODIFIED] Wait for initial config from client ---
        initial_config_raw = await websocket.receive_text()
        initial_config = json.loads(initial_config_raw).get("config", {})
        
        is_rag_enabled = initial_config.get("isRagEnabled", False)
        session_id = initial_config.get("sessionId")
        
        # The agent graph will handle the system prompt and context, so we don't need it here.
        # We just need to initialize the agent.
        agent = create_agent_graph()
        # --- End Modified Section ---

        config = LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="Puck"))
            ),
            # System instruction is now managed by the agent graph, so we can remove it here.
            # system_instruction=system_prompt,
        )

        async with client.aio.live.connect(model=MODEL, config=config) as session:
            end_time = time.time()
            setup_duration = end_time - start_time
            print(f"Gemini Live session started. Setup took: {setup_duration:.2f}s")

            # Send a confirmation message to the client with the setup time
            await websocket.send_text(
                json.dumps({
                    "status": "session_ready",
                    "setup_duration": setup_duration
                })
            )

            async def browser_to_gemini():
                while True:
                    try:
                        message = await websocket.receive_text()
                        data = json.loads(message)

                        if 'text' in data:
                            user_text = data['text']
                            print(f"Received text from user: {user_text}")

                            # Invoke the agent with the user's text
                            agent_response = agent.invoke(
                                {
                                    "messages": [HumanMessage(content=user_text)],
                                    "session_id": session_id,
                                    "use_rag": is_rag_enabled,
                                }
                            )
                            
                            response_text = agent_response['messages'][-1].content
                            print(f"Agent response: {response_text}")

                            # Send the agent's response back to Gemini to be spoken
                            await session.send_request(finalize_speech=FinalizeSpeechRequest(text=response_text))

                        if 'audio' in data:
                            audio_chunk = base64.b64decode(data['audio'])
                            await session.send_request(audio=[Blob(data=audio_chunk)])
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
                try:
                    async for response in session.receive():
                        if response.server_content and response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if part.inline_data:
                                    audio_data = part.inline_data.data
                                    base64_audio = base64.b64encode(audio_data).decode('utf-8')
                                    await websocket.send_text(json.dumps({"audio_chunk": base64_audio}))
                except asyncio.CancelledError:
                    print(f"Gemini-to-browser task cancelled for session {session_id}.")
                except Exception as e:
                    print(f"An unexpected error occurred in gemini_to_browser: {e}")
            
            await asyncio.gather(browser_to_gemini(), gemini_to_browser())

    except WebSocketDisconnect:
        print("WebSocket connection closed by client.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Live chat session ended.")