import { useState, useRef, useCallback } from 'react';
import toast from 'react-hot-toast';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';
type ConversationStatus = 'idle' | 'recording' | 'processing' | 'speaking';

const SAMPLE_RATE_FROM_GEMINI = 24000;
const SAMPLE_RATE_TO_GEMINI = 16000;

function createWavFile(pcmData: ArrayBuffer): ArrayBuffer {
    const sampleRate = SAMPLE_RATE_FROM_GEMINI;
    const numChannels = 1;
    const bytesPerSample = 2;
    const dataSize = pcmData.byteLength;
    const blockAlign = numChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true);
    writeString(view, 36, 'data');
    view.setUint32(40, dataSize, true);
    const pcmView = new Uint8Array(pcmData);
    const dataView = new Uint8Array(buffer, 44);
    dataView.set(pcmView);
    return buffer;
}

function writeString(view: DataView, offset: number, string: string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

// --- [MODIFIED] Hook now accepts initial configuration ---
export const useLiveVoiceChat = (isRagEnabled: boolean, sessionId: string) => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [conversationStatus, setConversationStatus] = useState<ConversationStatus>('idle');

  const socketRef = useRef<WebSocket | null>(null);
  const playbackAudioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const recordingAudioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioWorkletNodeRef = useRef<AudioWorkletNode | null>(null);

  const processAudioQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
    isPlayingRef.current = true;
    setConversationStatus('speaking');
    const rawPcmData = audioQueueRef.current.shift();
    if (rawPcmData && playbackAudioContextRef.current) {
      const wavData = createWavFile(rawPcmData);
      try {
        const audioBuffer = await playbackAudioContextRef.current.decodeAudioData(wavData);
        const source = playbackAudioContextRef.current.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(playbackAudioContextRef.current.destination);
        source.start();
        source.onended = () => {
          isPlayingRef.current = false;
          if (audioQueueRef.current.length > 0) {
            processAudioQueue();
          } else {
            setConversationStatus('idle');
          }
        };
      } catch (e) {
        console.error("Error playing audio:", e);
        isPlayingRef.current = false;
        setConversationStatus('idle');
      }
    } else {
        isPlayingRef.current = false;
        if(audioQueueRef.current.length === 0) setConversationStatus('idle');
    }
  }, []);

  const connect = useCallback(() => {
    if (socketRef.current || connectionStatus === 'connecting') return;
    setConnectionStatus('connecting');
    const ws = new WebSocket(`ws://localhost:8000/ws/v1/live-chat`);

    ws.onopen = () => {
      // --- [NEW] Send initial configuration on connect ---
      ws.send(JSON.stringify({
        config: {
          isRagEnabled: isRagEnabled,
          sessionId: sessionId
        }
      }));
      // ------------------------------------------------
      toast.success("Live connection established!");
      setConnectionStatus('connected');
      setConversationStatus('idle');
      playbackAudioContextRef.current = new (window.AudioContext)();
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.audio_chunk) {
            const byteString = atob(data.audio_chunk);
            const byteArray = new Uint8Array(byteString.length);
            for (let i = 0; i < byteString.length; i++) {
                byteArray[i] = byteString.charCodeAt(i);
            }
            audioQueueRef.current.push(byteArray.buffer);
            processAudioQueue();
        }
    };
    
    ws.onerror = () => {
      toast.error("Live connection error.");
      setConnectionStatus('error');
    };
    ws.onclose = () => {
      if(connectionStatus !== 'error') toast.success("Live connection closed.");
      setConnectionStatus('disconnected');
    };
    socketRef.current = ws;
  }, [connectionStatus, isRagEnabled, sessionId, processAudioQueue]);
  
  const startRecording = async () => {
    if (audioWorkletNodeRef.current) return;
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: SAMPLE_RATE_TO_GEMINI,
            },
        });
        mediaStreamRef.current = stream;
        recordingAudioContextRef.current = new AudioContext({ sampleRate: SAMPLE_RATE_TO_GEMINI });
        await recordingAudioContextRef.current.audioWorklet.addModule('/worklets/audio-processor.js');
        const workletNode = new AudioWorkletNode(
            recordingAudioContextRef.current, 
            'audio-processor',
            { processorOptions: { bufferSize: 4096 } }
        );
        audioWorkletNodeRef.current = workletNode;
        workletNode.port.onmessage = (event) => {
            if (socketRef.current?.readyState === WebSocket.OPEN) {
                const pcmData = new Uint8Array(event.data.pcmData);
                let binary = '';
                for (let i = 0; i < pcmData.byteLength; i++) {
                    binary += String.fromCharCode(pcmData[i]);
                }
                const base64Audio = btoa(binary);
                socketRef.current.send(JSON.stringify({ audio_chunk: base64Audio }));
            }
        };
        const source = recordingAudioContextRef.current.createMediaStreamSource(stream);
        source.connect(workletNode);
        setConversationStatus('recording');
    } catch (error) {
        toast.error("Could not start recording. Microphone permission needed.");
        console.error("Error starting recording:", error);
    }
  };
  
  const stopRecording = () => {
    if (mediaStreamRef.current) mediaStreamRef.current.getTracks().forEach(track => track.stop());
    if (audioWorkletNodeRef.current) {
        audioWorkletNodeRef.current.port.close();
        audioWorkletNodeRef.current.disconnect();
        audioWorkletNodeRef.current = null;
    }
    if (recordingAudioContextRef.current) {
        recordingAudioContextRef.current.close().then(() => {
            recordingAudioContextRef.current = null;
        });
    }
    setConversationStatus('processing');
  };

  const toggleRecording = () => {
    if (conversationStatus === 'idle') startRecording();
    else if (conversationStatus === 'recording') stopRecording();
  };
  
  const disconnect = () => {
    stopRecording();
    socketRef.current?.close();
    if (playbackAudioContextRef.current) {
        playbackAudioContextRef.current.close().then(() => {
            playbackAudioContextRef.current = null;
        });
    }
  };

  return { connectionStatus, conversationStatus, connect, disconnect, toggleRecording };
};