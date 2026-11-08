"use client";

import { useState, useRef } from "react";
import { UploadCloud, X, FileText, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import type { UploadBatch } from "@/lib/types";

interface ResumeUploadModalProps {
  requisitionId: string;
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (batch: UploadBatch) => void;
}

const MAX_FILE_SIZE = 15 * 1024 * 1024; // 15 MB
const MAX_FILES = 500;
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];

export default function ResumeUploadModal({
  requisitionId,
  isOpen,
  onClose,
  onUploadSuccess,
}: ResumeUploadModalProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  function validateAndAddFiles(files: FileList | File[]) {
    const newErrors: string[] = [];
    const validToAdd: File[] = [];

    if (selectedFiles.length + files.length > MAX_FILES) {
      newErrors.push(`Cannot exceed maximum limit of ${MAX_FILES} files per batch.`);
    }

    Array.from(files).forEach((file) => {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        newErrors.push(`"${file.name}": Unsupported file format. Only PDF and DOCX are allowed.`);
        return;
      }
      if (file.size === 0) {
        newErrors.push(`"${file.name}": File is empty (0 bytes).`);
        return;
      }
      if (file.size > MAX_FILE_SIZE) {
        newErrors.push(`"${file.name}": Exceeds maximum size limit of 15 MB.`);
        return;
      }

      // Check if duplicate in current selection
      const exists = selectedFiles.some(
        (f) => f.name === file.name && f.size === file.size
      );
      if (!exists) {
        validToAdd.push(file);
      }
    });

    setValidationErrors(newErrors);
    setSelectedFiles((prev) => [...prev, ...validToAdd]);
  }

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndAddFiles(e.dataTransfer.files);
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files.length > 0) {
      validateAndAddFiles(e.target.files);
    }
  }

  function removeFile(index: number) {
    setSelectedFiles((prev) => prev.filter((_, idx) => idx !== index));
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  async function handleUploadSubmit() {
    if (selectedFiles.length === 0) return;
    setIsUploading(true);
    setUploadProgress(20);

    try {
      setUploadProgress(50);
      const batch = await api.uploadResumes(requisitionId, selectedFiles);
      setUploadProgress(100);
      setTimeout(() => {
        setIsUploading(false);
        setSelectedFiles([]);
        onUploadSuccess(batch);
        onClose();
      }, 400);
    } catch (err: unknown) {
      setIsUploading(false);
      setValidationErrors([err instanceof Error ? err.message : "Failed to upload resumes."]);
    }
  }

  const totalBytes = selectedFiles.reduce((acc, f) => acc + f.size, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">Bulk Resume Ingestion</h2>
            <p className="text-xs text-slate-500">
              Upload PDF or DOCX resumes (up to 500 files, 15MB each).
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={isUploading}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          {/* Drag & Drop Area */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              isDragging
                ? "border-indigo-600 bg-indigo-50/50"
                : "border-slate-300 hover:border-slate-400 bg-slate-50/50"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileSelect}
              className="hidden"
            />
            <div className="w-12 h-12 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center mx-auto mb-3">
              <UploadCloud className="w-6 h-6" />
            </div>
            <p className="text-sm font-semibold text-slate-800">
              Drag & drop resumes here, or <span className="text-indigo-600">browse files</span>
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Supports PDF and DOCX documents with structured text or tables.
            </p>
          </div>

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-xs text-red-700 space-y-1">
              <div className="font-semibold flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4 text-red-600" />
                Upload Validation Issues:
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-red-600 pl-1">
                {validationErrors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Selected Files List */}
          {selectedFiles.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-600 font-medium">
                <span>
                  Selected Files: <strong>{selectedFiles.length}</strong> ({formatFileSize(totalBytes)})
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedFiles([])}
                  className="text-red-600 hover:underline text-xs"
                >
                  Clear all
                </button>
              </div>

              <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 max-h-48 overflow-y-auto bg-white">
                {selectedFiles.map((file, idx) => (
                  <div key={idx} className="p-2.5 px-3 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 truncate pr-2">
                      <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                      <span className="font-medium text-slate-800 truncate">{file.name}</span>
                      <span className="text-slate-400 shrink-0">({formatFileSize(file.size)})</span>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(idx);
                      }}
                      className="text-slate-400 hover:text-red-600 p-0.5 rounded"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upload Progress Bar */}
          {isUploading && (
            <div className="space-y-1.5 pt-2">
              <div className="flex justify-between text-xs font-semibold text-slate-700">
                <span>Uploading and initializing parsing pipeline...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isUploading}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 rounded-lg hover:bg-slate-100 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleUploadSubmit}
            disabled={selectedFiles.length === 0 || isUploading}
            className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isUploading ? "Uploading..." : `Upload ${selectedFiles.length} Resumes`}
          </button>
        </div>
      </div>
    </div>
  );
}
