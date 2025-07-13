import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from './ui/button';
import { Mic, PhoneOff, Loader2, Square } from 'lucide-react';
import { useLiveVoiceChat } from '@/hooks/useLiveVoiceChat';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';

interface LiveChatModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  isRagEnabled: boolean;
  sessionId: string;
}

const AudioVisualizer = () => (
  <div className="flex justify-center items-center gap-1 h-6">
    <span className="w-1 h-full bg-blue-500 rounded-full animate-[speak-1_1s_infinite]" />
    <span className="w-1 h-2/3 bg-blue-400 rounded-full animate-[speak-2_1s_infinite]" />
    <span className="w-1 h-full bg-blue-500 rounded-full animate-[speak-3_1s_infinite]" />
    <span className="w-1 h-1/2 bg-blue-400 rounded-full animate-[speak-2_1s_infinite]" />
    <span className="w-1 h-full bg-blue-500 rounded-full animate-[speak-1_1s_infinite]" />
  </div>
);

export function LiveChatModal({ isOpen, onOpenChange, isRagEnabled, sessionId }: LiveChatModalProps) {
  const { connectionStatus, conversationStatus, connect, disconnect, toggleRecording } = 
    useLiveVoiceChat(isRagEnabled, sessionId);

  useEffect(() => {
    if (isOpen && connectionStatus === 'disconnected') {
      connect();
    }
  }, [isOpen, connectionStatus, connect]);

  const handleEndCall = () => {
    disconnect();
    onOpenChange(false);
  };

  const renderStatusDescription = () => {
    switch (conversationStatus) {
      case 'recording': return "Listening... Click to stop.";
      case 'processing': return "Thinking...";
      case 'speaking': return "Assistant is speaking...";
      default: return isRagEnabled ? "Click to ask about your documents" : "Click the mic to start speaking";
    }
  };

  const canTalk = conversationStatus === 'idle' || conversationStatus === 'recording';

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleEndCall()}>
      <DialogContent onInteractOutside={(e) => e.preventDefault()} className="bg-gray-900">
        <DialogHeader>
          <DialogTitle>Live Voice Conversation {isRagEnabled && "(RAG Mode)"}</DialogTitle>
          <DialogDescription>{renderStatusDescription()}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center justify-center h-48 gap-4">
          {connectionStatus === 'connecting' && <Loader2 className="h-12 w-12 animate-spin text-muted-foreground" />}
          
          {connectionStatus === 'connected' && (
            <div className='flex flex-col items-center gap-4'>
              <div className="h-24 w-24 flex items-center justify-center">
                {conversationStatus === 'speaking' && <AudioVisualizer />}
                {conversationStatus === 'processing' && <Loader2 className="h-10 w-10 animate-spin text-blue-500" />}
              </div>
              <Button
                size="lg"
                className={cn("w-24 h-24 rounded-full transition-all duration-300 transform active:scale-95", {
                  "bg-blue-500 hover:bg-blue-600": conversationStatus === 'idle',
                  "bg-rose-600 hover:bg-rose-700 animate-breathing-glow": conversationStatus === 'recording',
                  "bg-gray-400 cursor-not-allowed": !canTalk,
                  "opacity-0": conversationStatus === 'processing' || conversationStatus === 'speaking' // Hide button when AI is busy
                })}
                onClick={toggleRecording}
                disabled={!canTalk}
              >
                {conversationStatus === 'recording' ? (
                    <Square className="h-8 w-8 fill-white" />
                ) : (
                    <Mic className="h-10 w-10" />
                )}
              </Button>
            </div>
          )}

          {connectionStatus === 'error' && <p className="text-red-500">Connection failed. Check permissions & console.</p>}
        </div>

        <DialogFooter>
          <Button variant="destructive" onClick={handleEndCall}>
            <PhoneOff className="mr-2 h-4 w-4" /> End Call
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}