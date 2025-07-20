import React, { useEffect, useState, useRef } from 'react';
import { Button } from './ui/button';
import { UploadCloud, File, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface UploadedFilesSidebarProps {
  sessionId: string;
}

const UploadedFilesSidebar: React.FC<UploadedFilesSidebarProps> = ({ sessionId }) => {
  const [files, setFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchFiles = async () => {
    if (!sessionId) return;
    try {
      const response = await fetch(`http://localhost:8000/api/v1/uploads/${sessionId}`);
      if (!response.ok) {
        if (response.status === 404) {
          setFiles([]);
          return;
        }
        throw new Error('Failed to fetch uploaded files.');
      }
      const data = await response.json();
      setFiles(data.files || []); // Ensure files is always an array
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred.');
      console.error("Error fetching files:", err);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile || !sessionId) return;

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`http://localhost:8000/api/v1/uploads/${sessionId}`,
        {
          method: 'POST',
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error('File upload failed');
      }
      
      // Refetch files to show the new one
      fetchFiles(); 
      // Dispatch event to notify other components if needed
      window.dispatchEvent(new CustomEvent('file-uploaded'));

    } catch (error) {
      console.error('Upload error:', error);
      setError('Upload failed. Please try again.');
    }
  };

  useEffect(() => {
    fetchFiles();
    const handleFileUploaded = () => fetchFiles();
    window.addEventListener('file-uploaded', handleFileUploaded);
    return () => {
      window.removeEventListener('file-uploaded', handleFileUploaded);
    };
  }, [sessionId]);

  return (
    <div className="w-80 bg-white dark:bg-black p-4 flex flex-col h-full border-l border-gray-200 dark:border-gray-800">
      <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Uploaded Documents</h2>
      
      <div className="flex-grow overflow-y-auto -mr-4 pr-4">
        {error && <p className="text-red-500 dark:text-red-400 text-xs mb-2">Error: {error}</p>}
        {files.length > 0 ? (
          <ul className="space-y-2">
            {files.map((file, index) => (
              <li key={index} className="flex items-center justify-between p-2 rounded-md bg-gray-100 dark:bg-gray-800/50">
                <div className="flex items-center gap-2 truncate">
                  <File className="h-4 w-4 text-gray-500 dark:text-gray-400 flex-shrink-0" />
                  <span className="text-sm text-gray-800 dark:text-gray-200 truncate">{file}</span>
                </div>
                {/* Optional: Add a delete button here if functionality exists */}
              </li>
            ))}
          </ul>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 dark:text-gray-400 border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-4">
            <UploadCloud className="h-8 w-8 mb-2" />
            <p className="text-sm font-medium">No documents uploaded</p>
            <p className="text-xs">Upload files to chat with them.</p>
          </div>
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileUpload}
          className="hidden"
          id="file-upload"
        />
        <Button onClick={() => fileInputRef.current?.click()} className="w-full">
          <UploadCloud className="mr-2 h-4 w-4" /> Upload File
        </Button>
      </div>
    </div>
  );
};

export default UploadedFilesSidebar;
