// src/hooks/useChat.ts
import { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import apiClient from '@/api/client';
import toast from 'react-hot-toast';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export const useChat = (sessionId: string, userEmail: string) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const loadChatHistory = async () => {
      if (!sessionId || !userEmail) return;
      setIsLoading(true);
      try {
        const response = await fetch(`http://localhost:8000/api/v1/history/session/${sessionId}?user_email=${encodeURIComponent(userEmail)}`);
        if (response.ok) {
          const history = await response.json();
          const formattedHistory = history.map((msg: any) => ({
            id: msg.id || uuidv4(),
            role: msg.role === 'human' ? 'user' : msg.role,
            content: msg.content,
          }));
          setMessages(formattedHistory);
        } else {
          setMessages([]);
        }
      } catch (error) {
        console.error('Failed to fetch chat history:', error);
        setMessages([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadChatHistory();
  }, [sessionId, userEmail]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  /**
   * Sends a message to the backend, including the RAG flag.
   */
  const sendMessage = async (
    e: React.FormEvent<HTMLFormElement>,
    isRagEnabled: boolean,
    isWebSearchEnabled: boolean
  ) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { id: uuidv4(), role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await apiClient.post('/chat', {
        session_id: sessionId,
        user_email: userEmail,
        message: input,
        use_rag: isRagEnabled,
        use_web_search: isWebSearchEnabled,
      });
      const botMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: response.data.response,
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'system',
        content: 'Error: Could not get a response. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const uploadFile = async (file: File) => {
    if (!file || isLoading) return;

    const uploadToastId = toast.loading(`Uploading ${file.name}...`);
    setIsLoading(true);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);

    try {
      const response = await fetch('http://localhost:8000/api/v1/upload_rag_docs', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'File upload failed');
      }
      
      toast.success(result.message || 'File uploaded successfully!', { id: uploadToastId });
      
      const systemMessageContent = `File "${file.name}" uploaded successfully. You can now enable the "Query Uploaded Files" switch to ask questions about it.`;
      const systemMessage: Message = {
        id: uuidv4(),
        role: 'system',
        content: systemMessageContent,
      };
      setMessages(prev => [...prev, systemMessage]);

      // Also send this system message to the backend to be saved in history
      try {
        await apiClient.post('/chat', {
          session_id: sessionId,
          user_email: userEmail,
          message: `(System: Uploaded file ${file.name})`, // User message is a system note
          use_rag: false, // This is not a user query
          use_web_search: false,
        });
      } catch (error) {
        console.error('Failed to save upload notification to chat history:', error);
      }

      // Notify the UI that a file has been uploaded so the list can refresh
      window.dispatchEvent(new CustomEvent('file-uploaded'));

    } catch (error: any) {
      toast.error(error.message || 'An error occurred during upload.', { id: uploadToastId });
    } finally {
      setIsLoading(false);
    }
  };

  return {
    messages,
    input,
    isLoading,
    handleInputChange,
    sendMessage,
    uploadFile,
    setMessages, // Expose setMessages for history functionality
  };
};