import { useState } from 'react';
import { useUser } from '@/context/UserContext';
import { useChat } from '@/hooks/useChat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from './ui/card';
import { Headphones, BrainCircuit } from 'lucide-react';
import { Button } from './ui/button';
import { LiveChatModal } from './LiveChatModal';
import { cn } from '@/lib/utils';
import ChatHistorySidebar from './ChatHistorySidebar';
import UploadedFilesSidebar from './UploadedFilesSidebar'; // Import the new right sidebar
import { v4 as uuidv4 } from 'uuid';

interface ChatLayoutProps {
  sessionId: string;
}

export function ChatLayout({ sessionId: initialSessionId }: ChatLayoutProps) {
  const [currentSessionId, setCurrentSessionId] = useState(initialSessionId);
  const { user } = useUser();

  // The useChat hook now handles loading history based on the session ID.
  const {
    messages,
    input,
    isLoading,
    handleInputChange,
    sendMessage,
    uploadFile,
  } = useChat(currentSessionId, user?.email || '');
  
  const [isTextRagEnabled, setIsTextRagEnabled] = useState(false);
  const [isWebSearchEnabled, setIsWebSearchEnabled] = useState(false);
  const [isLiveChatOpen, setIsLiveChatOpen] = useState(false);

  const [liveChatKey, setLiveChatKey] = useState(uuidv4());

  // Just update the session ID. The useChat hook will handle the rest.
  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
  };

  // Generate a new session ID. The useChat hook will see it's new and clear the messages.
  const handleNewChat = () => {
    setCurrentSessionId(uuidv4());
  };

  const handleOpenLiveChat = () => {
    setLiveChatKey(uuidv4()); // [FIX] Reset the key to force re-mount
    setIsLiveChatOpen(true);
  };

  const handleDeleteSession = async (sessionIdToDelete: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/history/sessions/${sessionIdToDelete}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete session.');
      }

      // Notify the sidebar to refetch the session list
      window.dispatchEvent(new CustomEvent('chat-deleted'));

      // If the currently active chat was deleted, start a new one.
      if (currentSessionId === sessionIdToDelete) {
        handleNewChat();
      }

    } catch (error) {
      console.error('Error deleting session:', error);
      // Optionally, show a toast notification for the error
    }
  };

  return (
    <div className="flex h-full w-full bg-gray-900">
      <ChatHistorySidebar 
        onSelectSession={handleSelectSession} 
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        currentSessionId={currentSessionId}
      />
      <div className="flex-1 flex flex-col p-4 overflow-hidden">
        <Card className="h-full w-full flex flex-col shadow-2xl bg-gray-900 border-gray-700">
      <CardHeader className="border-b border-gray-700 flex flex-row items-center justify-between p-4">
        <CardTitle className="text-gray-100">Multimodal AI Chatbot</CardTitle>
        <div className="flex items-center gap-4">

          {/* --- [THIS IS THE REPLACEMENT FOR THE SWITCH] --- */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsTextRagEnabled(!isTextRagEnabled)}
            className={cn(
              "text-gray-400 hover:text-gray-200",
              isTextRagEnabled && "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800"
            )}
          >
            <BrainCircuit className={cn("mr-2 h-4 w-4", isTextRagEnabled && "text-blue-500")} />
            RAG Mode
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsWebSearchEnabled(!isWebSearchEnabled)}
            className={cn(
              "text-gray-400 hover:text-gray-200",
              isWebSearchEnabled && "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800"
            )}
          >
            Web Search
          </Button>

          <Button variant="outline" size="sm" onClick={handleOpenLiveChat} className="text-gray-400 hover:text-gray-200">
            <Headphones className="mr-2 h-4 w-4" />
            Live Chat
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 overflow-y-auto">
        <MessageList messages={messages} isLoading={isLoading} />
      </CardContent>
      <CardFooter className="p-0 border-t">
        <ChatInput
          input={input}
          isLoading={isLoading}
          handleInputChange={handleInputChange}
          sendMessage={sendMessage}
          uploadFile={uploadFile}
          isRagEnabled={isTextRagEnabled}
          onRagToggle={setIsTextRagEnabled}
          isWebSearchEnabled={isWebSearchEnabled}
          onWebSearchToggle={setIsWebSearchEnabled}
        />
      </CardFooter>
      <LiveChatModal
        key={liveChatKey} // [FIX] Add key to force re-mount
        isOpen={isLiveChatOpen}
        onOpenChange={setIsLiveChatOpen}
        isRagEnabled={isTextRagEnabled}
        isWebSearchEnabled={isWebSearchEnabled}
        sessionId={currentSessionId}
      />
    </Card>
    </div>
    <UploadedFilesSidebar sessionId={currentSessionId} />
    </div>
  );
}