// src/App.tsx
import { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Toaster } from 'react-hot-toast';
import { ChatLayout } from '@/components/ChatLayout';
import { UserAuthModal } from '@/components/UserAuthModal';
import { useUser } from './context/UserContext';

function App() {
  const { user } = useUser();
  // Use the user's email as the session ID for persistence, or a new UUID if not logged in.
  const [sessionId] = useState(user ? user.email : uuidv4());

  return (
    <main className="flex flex-col h-screen w-screen items-center justify-center bg-gray-800 p-4">
      <UserAuthModal />
      <h1 className="text-4xl font-bold text-gray-100 mb-4">Okada Voice RAG Agent</h1>
      <Toaster position="top-center" />
      <ChatLayout sessionId={sessionId} />
    </main>
  );
}

export default App;