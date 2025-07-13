import React, { useEffect, useState } from 'react';

interface UploadedFilesSidebarProps {
  sessionId: string;
}

const UploadedFilesSidebar: React.FC<UploadedFilesSidebarProps> = ({ sessionId }) => {
  const [files, setFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchFiles = async () => {
    if (!sessionId) return;
    try {
      const response = await fetch(`http://localhost:8000/api/v1/uploads/${sessionId}`);
      if (!response.ok) {
        // It's normal for a new session to have no files, so we don't treat 404 as an error to display
        if (response.status === 404) {
          setFiles([]);
          return;
        }
        throw new Error('Failed to fetch uploaded files.');
      }
      const data = await response.json();
      setFiles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred.');
      console.error("Error fetching files:", err);
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
    <div className="w-64 bg-gray-800 text-white p-4 flex flex-col h-full border-l border-gray-700">
      <h2 className="text-lg font-semibold mb-2">Uploaded Documents</h2>
      {error && <p className="text-red-400">{error}</p>}
      <div className="flex-grow overflow-y-auto">
        {files.length > 0 ? (
          <ul>
            {files.map((file, index) => (
              <li key={index} className="p-2 rounded bg-gray-700 mb-2 truncate">
                {file}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-400 italic">No documents uploaded for this session.</p>
        )}
      </div>
    </div>
  );
};

export default UploadedFilesSidebar;
