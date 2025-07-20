import React, { useEffect, useState, useCallback } from 'react';
import { useUser } from '../context/UserContext';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Settings, Sun, Moon, Trash2, PlusCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Session {
  session_id: string;
  title: string;
}

interface ChatHistorySidebarProps {
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  onDeleteSession: (sessionId: string) => void;
  currentSessionId: string | null;
  theme: string;
  toggleTheme: () => void;
}

const ChatHistorySidebar: React.FC<ChatHistorySidebarProps> = ({ 
  onSelectSession, 
  onNewChat, 
  onDeleteSession, 
  currentSessionId, 
  theme, 
  toggleTheme 
}) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { user } = useUser();

  const fetchSessions = useCallback(async () => {
    if (!user?.email) {
      setSessions([]);
      return;
    }
    try {
      setError(null);
      const response = await fetch(`http://localhost:8000/api/v1/history/sessions/${user.email}`);
      if (!response.ok) {
        if (response.status === 404) {
          setSessions([]);
          return;
        }
        throw new Error('Failed to fetch chat sessions.');
      }
      const data = await response.json();
      setSessions(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
      setError(errorMessage);
      console.error("Error fetching sessions:", err);
    }
  }, [user?.email]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions, currentSessionId]);

  useEffect(() => {
    const handleStorageChange = () => fetchSessions();
    window.addEventListener('chat-deleted', handleStorageChange);
    return () => {
      window.removeEventListener('chat-deleted', handleStorageChange);
    };
  }, [fetchSessions]);

  return (
    <div className="w-80 bg-white dark:bg-black p-4 flex flex-col h-full border-r border-gray-200 dark:border-gray-800">
      <div className="flex flex-col mb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Okada Voice RAG</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">Agent</p>
      </div>
      
      <div className="flex items-center justify-between mb-6">
        <label htmlFor="theme-switch" className="text-sm font-medium text-gray-700 dark:text-gray-300">Theme</label>
        <div className="flex items-center gap-2">
          <Sun className="h-4 w-4 text-gray-500" />
          <Switch id="theme-switch" checked={theme === 'dark'} onCheckedChange={toggleTheme} />
          <Moon className="h-4 w-4 text-gray-500" />
        </div>
      </div>

      <Button onClick={onNewChat} className="w-full mb-4">
        <PlusCircle className="mr-2 h-4 w-4" /> New Chat
      </Button>

      <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Chat History</h2>
      {error && <p className="text-red-500 dark:text-red-400 text-xs">Error: {error}</p>}
      <div className="flex-grow overflow-y-auto -mr-4 pr-4">
        <ul className="space-y-1">
          {sessions.map((session) => (
            <li
              key={session.session_id}
              className={cn(
                "flex justify-between items-center p-2 rounded-md cursor-pointer transition-colors",
                "hover:bg-gray-100 dark:hover:bg-gray-800/50",
                session.session_id === currentSessionId ? 'bg-gray-100 dark:bg-gray-800/50' : ''
              )}
            >
              <span onClick={() => onSelectSession(session.session_id)} className="flex-grow truncate text-sm text-gray-800 dark:text-gray-200">
                {session.title || 'New Chat'}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(session.session_id);
                }}
                className="ml-2 p-1 rounded-full text-gray-400 hover:bg-red-500 hover:text-white transition-colors duration-200"
                aria-label={`Delete chat: ${session.title}`}
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-auto pt-4 border-t border-gray-200 dark:border-gray-800">
        <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
                <Avatar className="h-8 w-8">
                    <AvatarImage src={user?.picture} alt={user?.name} />
                    <AvatarFallback>{user?.name?.[0]}</AvatarFallback>
                </Avatar>
                <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{user?.name || 'Guest'}</span>
            </div>
            <Button variant="ghost" size="icon">
                <Settings className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            </Button>
        </div>
      </div>
    </div>
  );
}; 

export default ChatHistorySidebar;
