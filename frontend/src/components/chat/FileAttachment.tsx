import React, { useRef, useState } from 'react';
import {
  Paperclip,
  X,
  FileText,
  AlertCircle,
  FileCode,
  FileJson,
  Upload,
  RotateCw,
} from 'lucide-react';
import { Attachment } from '../../types/attachmentContract';

interface FileAttachmentProps {
  attachments: Attachment[];
  onAddFiles: (files: FileList | File[]) => void;
  onRemoveFile: (id: string) => void;
  onRetryFile?: (id: string) => void;
  isDragActive?: boolean;
}

export const FileAttachment: React.FC<FileAttachmentProps> = ({
  attachments,
  onAddFiles,
  onRemoveFile,
  onRetryFile,
  isDragActive = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOverZone, setDragOverZone] = useState<boolean>(false);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Specific icons based on file extension
  const getAttachmentIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'log':
        return <FileText className="w-3.5 h-3.5 text-rose-400 shrink-0" />;
      case 'py':
      case 'ts':
      case 'js':
      case 'sh':
        return <FileCode className="w-3.5 h-3.5 text-yellow-400 shrink-0" />;
      case 'json':
      case 'toml':
      case 'yaml':
        return <FileJson className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
      case 'md':
      case 'txt':
      default:
        return <FileText className="w-3.5 h-3.5 text-sky-400 shrink-0" />;
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverZone(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onAddFiles(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverZone(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverZone(false);
  };

  return (
    <div className="w-full">
      {/* Hidden File Picker Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            onAddFiles(e.target.files);
            // Reset input so same file can be re-uploaded if desired
            e.target.value = '';
          }
        }}
        multiple
        className="hidden"
      />

      {/* Visual Drag & Drop Overlay Zone when user drags over */}
      {(dragOverZone || isDragActive) && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className="mb-2 p-3 border-2 border-dashed border-sky-400/80 bg-sky-500/10 rounded-xl flex items-center justify-center space-x-2 text-xs text-sky-300 animate-pulse select-none"
        >
          <Upload className="w-4 h-4 text-sky-400" />
          <span className="font-medium">Drop files to attach (logs, configs, requirements, code)</span>
        </div>
      )}

      {/* Uploaded / Uploading File Chips Preview */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 pb-2">
          {attachments.map((file) => {
            const isUploading = file.status === 'uploading';
            const isError = file.status === 'error';

            return (
              <div
                key={file.id}
                className={`relative flex items-center space-x-2 px-2.5 py-1.5 rounded-lg border text-xs transition shadow-xs max-w-[240px] select-none ${
                  isError
                    ? 'bg-rose-950/40 border-rose-500/60 text-rose-200'
                    : isUploading
                    ? 'bg-harness-panel/80 border-sky-500/40 text-gray-200'
                    : 'bg-harness-bg border-harness-border hover:border-gray-600 text-gray-200'
                }`}
                title={isError ? file.error || 'Upload error' : `${file.name} (${formatFileSize(file.size)})`}
              >
                {/* File type icon */}
                {isError ? (
                  <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                ) : (
                  getAttachmentIcon(file.name)
                )}

                {/* File details: Name & Size */}
                <div className="flex flex-col min-w-0 flex-1">
                  <div className="flex items-center space-x-1">
                    <span className="truncate font-medium text-[11px]">{file.name}</span>
                  </div>
                  <div className="flex items-center space-x-1.5 text-[10px] text-gray-400">
                    <span>{formatFileSize(file.size)}</span>
                    {isUploading && (
                      <span className="text-sky-400 font-mono">
                        {file.progress}%
                      </span>
                    )}
                    {isError && (
                      <span className="text-rose-400 font-medium truncate max-w-[100px]">
                        {file.error || 'Failed'}
                      </span>
                    )}
                  </div>

                  {/* Upload Progress Bar */}
                  {isUploading && (
                    <div className="w-full bg-harness-border/60 rounded-full h-1 mt-1 overflow-hidden">
                      <div
                        className="bg-sky-400 h-1 rounded-full transition-all duration-150"
                        style={{ width: `${Math.max(5, file.progress)}%` }}
                      />
                    </div>
                  )}
                </div>

                {/* Retry Button on Error */}
                {isError && onRetryFile && (
                  <button
                    type="button"
                    onClick={() => onRetryFile(file.id)}
                    className="p-1 hover:text-white rounded hover:bg-rose-900/50 text-rose-300 transition"
                    title="Retry upload"
                  >
                    <RotateCw className="w-3 h-3" />
                  </button>
                )}

                {/* Remove Attachment Button */}
                <button
                  type="button"
                  onClick={() => onRemoveFile(file.id)}
                  className="p-0.5 rounded text-gray-400 hover:text-rose-400 hover:bg-harness-panel transition"
                  title="Remove attachment"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* File Picker Trigger Button */}
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        className="flex items-center space-x-1 p-1.5 text-gray-400 hover:text-gray-200 hover:bg-harness-panel rounded-md transition text-xs select-none"
        title="Attach files (logs, requirements, markdown, code)"
      >
        <Paperclip className="w-4 h-4" />
        <span className="text-[11px] text-gray-400">Attach</span>
      </button>
    </div>
  );
};
