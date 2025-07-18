import React, { useEffect, useState, useCallback } from 'react';
import { useUser } from '../context/UserContext'; // Import the useUser hook

interface Session {
  session_id: string;
  title: string;
}

interface ChatHistorySidebarProps {
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  onDeleteSession: (sessionId: string) => void; // For the new delete functionality
  currentSessionId: string | null;
}

const ChatHistorySidebar: React.FC<ChatHistorySidebarProps> = ({ onSelectSession, onNewChat, onDeleteSession, currentSessionId }) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { user } = useUser(); // Get the authenticated user

  const fetchSessions = useCallback(async () => {
    if (!user?.email) {
      setSessions([]); // Clear sessions if no user is logged in
      return;
    }
    try {
      setError(null);
      const response = await fetch(`http://localhost:8000/api/v1/history/sessions/${user.email}`);
      if (!response.ok) {
        // A 404 is not necessarily an error to display, it could just mean no history.
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
  }, [fetchSessions, currentSessionId]); // Refetch when session changes or user logs in

  // Expose a refetch function to be called after deletion
  useEffect(() => {
    const handleStorageChange = () => fetchSessions();
    window.addEventListener('chat-deleted', handleStorageChange);
    return () => {
      window.removeEventListener('chat-deleted', handleStorageChange);
    };
  }, []);

  return (
    <div className="w-64 bg-gray-800 text-white p-4 flex flex-col h-full">
      <button
        onClick={onNewChat}
        className="mb-4 w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded transition duration-300"
      >
        + New Chat
      </button>
      <h2 className="text-lg font-semibold mb-2">Chat History</h2>
      {error && <p className="text-red-400">{error}</p>}
      <div className="flex-grow overflow-y-auto">
        <ul>
          {sessions.map((session) => (
            <li
              key={session.session_id}
              className={`flex justify-between items-center p-2 rounded cursor-pointer hover:bg-gray-700 ${
                session.session_id === currentSessionId ? 'bg-gray-700' : ''
              }`}
            >
              <span onClick={() => onSelectSession(session.session_id)} className="flex-grow truncate">
                {session.title}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation(); // Prevent the li's onClick from firing
                  onDeleteSession(session.session_id);
                }}
                className="ml-2 p-1 rounded-full text-gray-400 hover:bg-red-500 hover:text-white transition-colors duration-200"
                aria-label={`Delete chat: ${session.title}`}
              >
                &#x2715; {/* A simple 'X' character for the delete icon */}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default ChatHistorySidebar;
