import { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Toaster } from 'sonner';
import { ChatLayout } from '@/components/ChatLayout';
import { UserAuthModal } from '@/components/UserAuthModal';
import { useUser } from './context/UserContext';
import { cn } from './lib/utils';

function App() {
  const { user } = useUser();
  const [sessionId] = useState(user ? user.email || uuidv4() : uuidv4());

  // Simple theme state for toggling light/dark mode
  const [theme, setTheme] = useState('light'); 

  const toggleTheme = () => {
    setTheme(currentTheme => (currentTheme === 'light' ? 'dark' : 'light'));
  };

  return (
    <main className={cn(
      "flex h-screen w-screen items-center justify-center bg-gray-100 p-4 font-sans",
      theme === 'dark' && 'dark' // Apply dark class to the main element
    )}>
      <div className="w-full max-w-screen-xl h-full max-h-[95vh] bg-white dark:bg-black rounded-2xl shadow-2xl flex overflow-hidden">
        <UserAuthModal />
        <Toaster position="top-center" theme={theme} />
        <ChatLayout 
          sessionId={sessionId} 
          theme={theme}
          toggleTheme={toggleTheme} 
        />
      </div>
    </main>
  );
}

export default App;