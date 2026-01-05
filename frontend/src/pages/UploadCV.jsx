import { useState, useRef } from 'react'
import {
  Upload,
  FileText,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import { cvService } from '../services/api'

export default function UploadCV() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null) // 'success' | 'error' | null
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  const handleFileSelect = (selectedFile) => {
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ]

    if (!allowedTypes.includes(selectedFile.type)) {
      setUploadStatus('error')
      return
    }

    setFile(selectedFile)
    setUploadStatus(null)
  }

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setUploadStatus(null)

    try {
      await cvService.uploadCV(file)
      setUploadStatus('success')
      setFile(null)
    } catch (error) {
      console.error('Upload failed:', error)
      setUploadStatus('error')
    } finally {
      setUploading(false)
    }
  }

  const removeFile = () => {
    setFile(null)
    setUploadStatus(null)
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Upload Your CV</h1>
        <p className="mt-1 text-text-secondary">
          Upload your base CV to start matching with job opportunities
        </p>
      </div>

      {/* Upload Area */}
      <div
        className={`relative border-2 border-dashed rounded-2xl p-8 transition-colors ${
          dragActive
            ? 'border-accent-500 bg-accent-500/5'
            : 'border-border hover:border-text-muted'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.doc,.docx"
          onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
          className="hidden"
        />

        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-surface-elevated mx-auto flex items-center justify-center mb-4">
            <Upload className="w-8 h-8 text-text-muted" />
          </div>
          <h3 className="text-lg font-medium text-text-primary mb-2">
            Drag and drop your CV here
          </h3>
          <p className="text-text-secondary mb-4">
            or click to browse from your computer
          </p>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="btn-secondary"
          >
            Select File
          </button>
          <p className="mt-4 text-sm text-text-muted">
            Supported formats: PDF, DOC, DOCX (max 10MB)
          </p>
        </div>
      </div>

      {/* Selected File */}
      {file && (
        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-accent-500/10 flex items-center justify-center">
            <FileText className="w-6 h-6 text-accent-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-text-primary truncate">{file.name}</p>
            <p className="text-sm text-text-muted">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          <button
            onClick={removeFile}
            className="btn-icon text-text-muted hover:text-red-400"
            aria-label="Remove file"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Status Messages */}
      {uploadStatus === 'success' && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <div>
            <p className="font-medium text-emerald-400">Upload successful</p>
            <p className="text-sm text-emerald-400/80">
              Your CV has been uploaded and is being analyzed
            </p>
          </div>
        </div>
      )}

      {uploadStatus === 'error' && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <div>
            <p className="font-medium text-red-400">Upload failed</p>
            <p className="text-sm text-red-400/80">
              Please try again or use a different file format
            </p>
          </div>
        </div>
      )}

      {/* Upload Button */}
      {file && (
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="btn-primary w-full"
        >
          {uploading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="w-5 h-5" />
              Upload CV
            </>
          )}
        </button>
      )}

      {/* Tips */}
      <div className="card-elevated">
        <h3 className="font-medium text-text-primary mb-4">Tips for a better CV</h3>
        <ul className="space-y-3 text-sm text-text-secondary">
          <li className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-accent-400 mt-0.5 flex-shrink-0" />
            <span>Keep your CV concise and focused on relevant experience</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-accent-400 mt-0.5 flex-shrink-0" />
            <span>Use clear section headings and bullet points</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-accent-400 mt-0.5 flex-shrink-0" />
            <span>Include quantifiable achievements where possible</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-accent-400 mt-0.5 flex-shrink-0" />
            <span>Ensure your contact information is up to date</span>
          </li>
        </ul>
      </div>
    </div>
  )
}
