import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from './ui/button';
import { Mic, PhoneOff, Loader2, Square, X } from 'lucide-react';
import { useLiveVoiceChat, type Transcript } from '@/hooks/useLiveVoiceChat';
import { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

interface LiveChatModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  isRagEnabled: boolean;
  isWebSearchEnabled: boolean;
  sessionId: string;
}

export function LiveChatModal({ isOpen, onOpenChange, isRagEnabled, isWebSearchEnabled, sessionId }: LiveChatModalProps) {
  const {
    connectionStatus,
    conversationStatus,
    transcripts,
    connect,
    disconnect,
    toggleRecording,
  } = useLiveVoiceChat(isRagEnabled, isWebSearchEnabled, sessionId);

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
      case 'recording': return "Listening... Click the icon to stop.";
      case 'processing': return "The AI is thinking...";
      case 'speaking': return "The AI is responding...";
      default:
        return "Click the mic to start speaking";
    }
  };

  const canTalk = conversationStatus === 'idle' || conversationStatus === 'recording';

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleEndCall()}>
      <DialogContent className="max-w-md w-full bg-white dark:bg-black rounded-2xl shadow-2xl p-6" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader className="text-center">
          <DialogTitle className="text-xl font-bold text-gray-900 dark:text-gray-100">Live Voice Conversation</DialogTitle>
          <DialogDescription className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {renderStatusDescription()}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center justify-center h-64 my-8">
          {connectionStatus === 'connecting' && <Loader2 className="h-16 w-16 animate-spin text-blue-500" />}
          
          {connectionStatus === 'connected' && (
            <div className="relative flex items-center justify-center w-48 h-48">
              <div className={cn(
                "absolute inset-0 bg-blue-100 dark:bg-blue-900/50 rounded-full transition-transform duration-500 ease-in-out",
                (conversationStatus === 'recording' || conversationStatus === 'speaking') ? 'scale-100' : 'scale-75',
                conversationStatus === 'speaking' && 'animate-pulse-strong'
              )} />
              <Button
                size="lg"
                className={cn(
                  "relative w-24 h-24 rounded-full transition-all duration-300 transform shadow-lg",
                  "flex items-center justify-center",
                  {
                    "bg-blue-500 hover:bg-blue-600 text-white": conversationStatus === 'idle',
                    "bg-red-500 hover:bg-red-600 text-white": conversationStatus === 'recording',
                    "bg-gray-400 cursor-not-allowed": !canTalk,
                  }
                )}
                onClick={toggleRecording}
                disabled={!canTalk}
              >
                {conversationStatus === 'processing' ? (
                  <Loader2 className="h-10 w-10 animate-spin" />
                ) : conversationStatus === 'recording' ? (
                  <Square className="h-8 w-8 fill-white" />
                ) : (
                  <Mic className="h-10 w-10" />
                )}
              </Button>
            </div>
          )}

          {connectionStatus === 'error' && (
            <div className="text-center text-red-500">
              <p className="font-semibold">Connection Failed</p>
              <p className="text-xs">Please check mic permissions and reload.</p>
            </div>
          )}
        </div>

        <DialogFooter className="flex !flex-row justify-center">
          <Button variant="destructive" onClick={handleEndCall} className="w-full max-w-xs">
            <PhoneOff className="mr-2 h-4 w-4" /> End Call
          </Button>
        </DialogFooter>
        
        
      </DialogContent>
    </Dialog>
  );
}