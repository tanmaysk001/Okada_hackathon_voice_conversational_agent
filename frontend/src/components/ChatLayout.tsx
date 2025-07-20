import { useState } from 'react';
import { useUser } from '@/context/UserContext';
import { useChat } from '@/hooks/useChat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from './ui/card';
import { Headphones, BrainCircuit, Search } from 'lucide-react';
import { Button } from './ui/button';
import { LiveChatModal } from './LiveChatModal';
import { cn } from '@/lib/utils';
import ChatHistorySidebar from './ChatHistorySidebar';
import UploadedFilesSidebar from './UploadedFilesSidebar';
import { v4 as uuidv4 } from 'uuid';

interface ChatLayoutProps {
  sessionId: string;
  theme: string;
  toggleTheme: () => void;
}

export function ChatLayout({ sessionId: initialSessionId, theme, toggleTheme }: ChatLayoutProps) {
  const [currentSessionId, setCurrentSessionId] = useState(initialSessionId);
  const { user } = useUser();

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

  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
  };

  const handleNewChat = () => {
    setCurrentSessionId(uuidv4());
  };

  const handleOpenLiveChat = () => {
    setLiveChatKey(uuidv4());
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

      window.dispatchEvent(new CustomEvent('chat-deleted'));

      if (currentSessionId === sessionIdToDelete) {
        handleNewChat();
      }

    } catch (error) {
      console.error('Error deleting session:', error);
    }
  };

  return (
    <div className="flex h-full w-full bg-white dark:bg-black text-black dark:text-white">
      <ChatHistorySidebar 
        onSelectSession={handleSelectSession} 
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        currentSessionId={currentSessionId}
        theme={theme}
        toggleTheme={toggleTheme}
      />
      <div className="flex-1 flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-900/50">
        <header className="border-b border-gray-200 dark:border-gray-800 flex items-center justify-between p-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Multimodal AI Chatbot</h2>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsTextRagEnabled(!isTextRagEnabled)}
              className={cn(
                "text-gray-600 dark:text-gray-400 border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800",
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
                "text-gray-600 dark:text-gray-400 border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800",
                isWebSearchEnabled && "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800"
              )}
            >
              <Search className="mr-2 h-4 w-4" />
              Web Search
            </Button>
            <Button variant="primary" size="sm" onClick={handleOpenLiveChat}>
              <Headphones className="mr-2 h-4 w-4" />
              Live Chat
            </Button>
          </div>
        </header>
        <div className="flex-1 p-4 overflow-y-auto">
          <MessageList messages={messages} isLoading={isLoading} />
        </div>
        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
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
        </div>
      </div>
      <UploadedFilesSidebar sessionId={currentSessionId} />
      <LiveChatModal
        key={liveChatKey}
        isOpen={isLiveChatOpen}
        onOpenChange={setIsLiveChatOpen}
        isRagEnabled={isTextRagEnabled}
        isWebSearchEnabled={isWebSearchEnabled}
        sessionId={currentSessionId}
      />
    </div>
  );
}