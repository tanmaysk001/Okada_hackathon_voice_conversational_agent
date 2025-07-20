// src/components/ChatInput.tsx
import { Paperclip, SendHorizonal, Loader2, BrainCircuit, Globe } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { useRef } from 'react';
import { cn } from '@/lib/utils'; // Import the cn utility for conditional classes
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip" // Import Tooltip components


interface ChatInputProps {
  input: string;
  isLoading: boolean;
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  sendMessage: (
    e: React.FormEvent<HTMLFormElement>,
    isRagEnabled: boolean,
    isWebSearchEnabled: boolean
  ) => void;
  uploadFile: (file: File) => void;
  isRagEnabled: boolean;
  onRagToggle: (enabled: boolean) => void;
  isWebSearchEnabled: boolean;
  onWebSearchToggle: (enabled: boolean) => void;
}

export function ChatInput({
  input,
  isLoading,
  handleInputChange,
  sendMessage,
  uploadFile,
  isRagEnabled,
  onRagToggle,
  isWebSearchEnabled,
  onWebSearchToggle,
}: ChatInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
      onRagToggle(true); // Automatically enable RAG mode on file upload
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="p-4 bg-black w-full">
      <div className="flex items-center gap-2">
        <Input
          id="file-upload"
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
          disabled={isLoading}
        />
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={handleUploadClick}
                disabled={isLoading}
                aria-label="Upload file"
                className="text-gray-400 hover:text-gray-200"
              >
                <Paperclip className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Upload File (Enables RAG)</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
        
        {/* The main chat input form */}
        <form onSubmit={(e) => sendMessage(e, isRagEnabled, isWebSearchEnabled)} className="flex-1 flex items-center gap-2">
          <Input
            value={input}
            onChange={handleInputChange}
            placeholder={isRagEnabled ? "Ask about your documents..." : "Ask me anything..."}
            autoComplete="off"
            disabled={isLoading}
            className="flex-1 bg-black border-gray-700 text-gray-200 placeholder-gray-500"
          />
          <Button type="submit" size="icon" disabled={isLoading || !input.trim()} aria-label="Send message" className="bg-blue-600 hover:bg-blue-700 text-white">
            {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <SendHorizonal className="h-5 w-5" />}
          </Button>
        </form>

        {/* --- THIS IS THE NEW, IMPROVED RAG TOGGLE BUTTON --- */}
        <TooltipProvider>
            <Tooltip>
                <TooltipTrigger asChild>
                    <Button
                    type="button"
                    variant={isRagEnabled ? "secondary" : "ghost"} // Change variant based on state
                    size="icon"
                    onClick={() => onRagToggle(!isRagEnabled)} // Simple toggle on click
                    disabled={isLoading}
                    aria-label="Toggle RAG mode"
                    className={cn("text-gray-400 hover:text-gray-200", {
                        "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300": isRagEnabled,
                    })}
                    >
                    <BrainCircuit className="h-5 w-5" />
                    </Button>
                </TooltipTrigger>
                <TooltipContent>
                    <p>Query Uploaded Files</p>
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>

        {/* --- THIS IS THE NEW WEB SEARCH TOGGLE BUTTON --- */}
        <TooltipProvider>
            <Tooltip>
                <TooltipTrigger asChild>
                    <Button
                    type="button"
                    variant={isWebSearchEnabled ? "secondary" : "ghost"} // Change variant based on state
                    size="icon"
                    onClick={() => onWebSearchToggle(!isWebSearchEnabled)} // Simple toggle on click
                    disabled={isLoading}
                    aria-label="Toggle Web Search"
                    className={cn("text-gray-400 hover:text-gray-200", {
                        "bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300": isWebSearchEnabled,
                    })}
                    >
                    <Globe className="h-5 w-5" />
                    </Button>
                </TooltipTrigger>
                <TooltipContent>
                    <p>Enable/Disable Web Search</p>
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>

      </div>
    </div>
  );
}