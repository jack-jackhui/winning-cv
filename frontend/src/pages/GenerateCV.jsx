import { useState, useRef, useCallback, useEffect } from 'react'
import {
  FileText,
  Download,
  Loader2,
  Upload,
  X,
  CheckCircle2,
  AlertCircle,
  Eye,
  Copy,
  ExternalLink,
  FolderOpen,
  Plus,
  ChevronDown,
  BarChart3,
  Save,
  Edit3,
  Library,
} from 'lucide-react'
import { cvService, cvVersionsService } from '../services/api'
import CVSelector from '../components/cv/CVSelector'
import AnalysisModal from '../components/cv/AnalysisModal'

export default function GenerateCV() {
  // CV source state: 'library' | 'upload'
  const [cvSource, setCvSource] = useState('library')

  // File upload state (for upload mode)
  const [cvFile, setCvFile] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)

  // Library selection state (for library mode)
  const [selectedVersion, setSelectedVersion] = useState(null)

  // Form state
  const [jobDescription, setJobDescription] = useState('')
  const [instructions, setInstructions] = useState('')

  // Generation state
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Preview state
  const [showPreview, setShowPreview] = useState(true)
  const [copied, setCopied] = useState(false)
  const [showDownloadMenu, setShowDownloadMenu] = useState(false)
  const downloadMenuRef = useRef(null)

  // Analysis state
  const [analysisStatus, setAnalysisStatus] = useState('idle') // idle | pending | ready | failed
  const [analysis, setAnalysis] = useState(null)
  const [showAnalysisModal, setShowAnalysisModal] = useState(false)
  const analysisPollingRef = useRef(null)

  // Auto-save to library state
  const [savedToLibrary, setSavedToLibrary] = useState(null) // { version_id, version_name } or null
  const [savingToLibrary, setSavingToLibrary] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [editingName, setEditingName] = useState(false)
  const [customVersionName, setCustomVersionName] = useState('')

  // Close download menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (downloadMenuRef.current && !downloadMenuRef.current.contains(event.target)) {
        setShowDownloadMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Cleanup analysis polling on unmount
  useEffect(() => {
    return () => {
      if (analysisPollingRef.current) {
        clearInterval(analysisPollingRef.current)
      }
    }
  }, [])

  // Poll for analysis status
  const startAnalysisPolling = useCallback((historyId) => {
    if (!historyId) return

    setAnalysisStatus('pending')
    setAnalysis(null)

    // Poll every 3 seconds
    analysisPollingRef.current = setInterval(async () => {
      try {
        const response = await cvService.getAnalysis(historyId)

        if (response.status === 'ready') {
          clearInterval(analysisPollingRef.current)
          setAnalysisStatus('ready')
          setAnalysis(response)
        } else if (response.status === 'failed') {
          clearInterval(analysisPollingRef.current)
          setAnalysisStatus('failed')
          setAnalysis(null)
        }
        // If still pending, continue polling
      } catch (err) {
        console.error('Failed to fetch analysis:', err)
        // Don't stop polling on transient errors
      }
    }, 3000)

    // Also do an immediate check
    cvService.getAnalysis(historyId).then(response => {
      if (response.status === 'ready') {
        clearInterval(analysisPollingRef.current)
        setAnalysisStatus('ready')
        setAnalysis(response)
      } else if (response.status === 'failed') {
        clearInterval(analysisPollingRef.current)
        setAnalysisStatus('failed')
      }
    }).catch(() => {})
  }, [])

  // Auto-save generated CV to library
  const saveToLibrary = useCallback(async (historyId, jobTitle, customName = null) => {
    if (!historyId || savingToLibrary) return

    setSavingToLibrary(true)
    setSaveError(null)

    try {
      const versionName = customName || `${jobTitle} (${new Date().toLocaleDateString('en-AU', { month: 'short', year: 'numeric' })})`
      const savedVersion = await cvVersionsService.createFromHistory(historyId, {
        versionName,
        autoCategory: 'Generated',
        userTags: ['generated', 'auto-saved'],
      })

      setSavedToLibrary({
        version_id: savedVersion.version_id,
        version_name: savedVersion.version_name,
      })
      setCustomVersionName(savedVersion.version_name)
    } catch (err) {
      console.error('Failed to save to library:', err)
      setSaveError(err.message || 'Failed to save to library')
    } finally {
      setSavingToLibrary(false)
    }
  }, [savingToLibrary])

  // Update version name in library
  const updateVersionName = async () => {
    if (!savedToLibrary || !customVersionName.trim()) return

    try {
      await cvVersionsService.updateVersion(savedToLibrary.version_id, {
        versionName: customVersionName.trim(),
      })
      setSavedToLibrary(prev => ({ ...prev, version_name: customVersionName.trim() }))
      setEditingName(false)
    } catch (err) {
      console.error('Failed to update version name:', err)
    }
  }

  // Remove from library (delete the auto-saved version)
  const removeFromLibrary = async () => {
    if (!savedToLibrary) return

    try {
      await cvVersionsService.deleteVersion(savedToLibrary.version_id)
      setSavedToLibrary(null)
      setCustomVersionName('')
    } catch (err) {
      console.error('Failed to remove from library:', err)
    }
  }

  const handleDrag = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      if (isValidFile(file)) {
        setCvFile(file)
        setError(null)
      } else {
        setError('Please upload a PDF, DOCX, or TXT file')
      }
    }
  }, [])

  const isValidFile = (file) => {
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
    ]
    return validTypes.includes(file.type)
  }

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      if (isValidFile(file)) {
        setCvFile(file)
        setError(null)
      } else {
        setError('Please upload a PDF, DOCX, or TXT file')
      }
    }
  }

  const handleRemoveFile = () => {
    setCvFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleVersionSelect = (version) => {
    setSelectedVersion(version)
    setError(null)
  }

  const handleCreateNew = () => {
    setCvSource('upload')
    setSelectedVersion(null)
  }

  const handleGenerate = async () => {
    // Validate CV source
    if (cvSource === 'library' && !selectedVersion) {
      setError('Please select a CV from your library or upload a new one')
      return
    }
    if (cvSource === 'upload' && !cvFile) {
      setError('Please upload your CV')
      return
    }
    if (!jobDescription.trim()) {
      setError('Please enter a job description')
      return
    }
    if (jobDescription.trim().length < 50) {
      setError('Please enter a more detailed job description (at least 50 characters)')
      return
    }

    setGenerating(true)
    setError(null)
    setResult(null)

    try {
      let response

      if (cvSource === 'library' && selectedVersion) {
        // Using CV from library - fetch the file first
        const { download_url } = await cvVersionsService.getDownloadUrl(selectedVersion.version_id)

        // Fetch the file from the download URL
        const fileResponse = await fetch(download_url)
        const blob = await fileResponse.blob()
        const file = new File([blob], selectedVersion.file_name || 'cv.pdf', {
          type: blob.type || 'application/pdf',
        })

        response = await cvService.generateCV(jobDescription, file, instructions)

        // Record usage of this CV version
        await cvVersionsService.recordUsage(selectedVersion.version_id)
      } else {
        // Using uploaded file
        response = await cvService.generateCV(jobDescription, cvFile, instructions)
      }

      setResult(response)

      // Start polling for analysis if history_id is available
      if (response.history_id) {
        startAnalysisPolling(response.history_id)

        // Auto-save to library
        saveToLibrary(response.history_id, response.job_title)
      }
    } catch (err) {
      setError(err.message || 'Failed to generate CV. Please try again.')
    } finally {
      setGenerating(false)
    }
  }

  const handleDownload = (format = 'pdf') => {
    setShowDownloadMenu(false)
    if (format === 'pdf' && result?.cv_pdf_url) {
      cvService.downloadFromUrl(result.cv_pdf_url, `${result.job_title}_cv.pdf`)
    } else if (format === 'docx' && result?.cv_docx_url) {
      cvService.downloadFromUrl(result.cv_docx_url, `${result.job_title}_cv.docx`)
    }
  }

  const handleCopyMarkdown = async () => {
    if (result?.cv_markdown) {
      try {
        await navigator.clipboard.writeText(result.cv_markdown)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (err) {
        console.error('Failed to copy:', err)
      }
    }
  }

  const handleReset = () => {
    // Stop any ongoing analysis polling
    if (analysisPollingRef.current) {
      clearInterval(analysisPollingRef.current)
    }

    setCvSource('library')
    setCvFile(null)
    setSelectedVersion(null)
    setJobDescription('')
    setInstructions('')
    setResult(null)
    setError(null)
    setAnalysisStatus('idle')
    setAnalysis(null)
    // Reset library save state
    setSavedToLibrary(null)
    setSavingToLibrary(false)
    setSaveError(null)
    setEditingName(false)
    setCustomVersionName('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Generate Tailored CV</h1>
        <p className="mt-1 text-text-secondary">
          Upload your CV and paste a job description to generate a customized resume
        </p>
      </div>

      {result ? (
        // Result View
        <div className="space-y-6">
          {/* Success Banner */}
          <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-medium text-emerald-400">CV Generated Successfully</p>
              <p className="text-sm text-emerald-400/80">
                Tailored for: {result.job_title}
              </p>
            </div>
            <button onClick={handleReset} className="btn-secondary text-sm">
              Generate Another
            </button>
          </div>

          {/* Library Save Status */}
          <div className="p-4 rounded-xl bg-surface-elevated border border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-accent-500/10 flex items-center justify-center">
                <Library className="w-5 h-5 text-accent-400" />
              </div>
              <div className="flex-1 min-w-0">
                {savingToLibrary ? (
                  <div className="flex items-center gap-2 text-text-secondary">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Saving to My CVs...</span>
                  </div>
                ) : savedToLibrary ? (
                  <div className="space-y-1">
                    <p className="text-sm text-text-muted">Saved to My CVs as:</p>
                    {editingName ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={customVersionName}
                          onChange={(e) => setCustomVersionName(e.target.value)}
                          className="input py-1 px-2 text-sm flex-1"
                          onKeyDown={(e) => e.key === 'Enter' && updateVersionName()}
                          autoFocus
                        />
                        <button
                          onClick={updateVersionName}
                          className="btn-icon text-emerald-400 hover:bg-emerald-500/10"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            setEditingName(false)
                            setCustomVersionName(savedToLibrary.version_name)
                          }}
                          className="btn-icon text-text-muted hover:text-text-primary"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-text-primary truncate">
                          {savedToLibrary.version_name}
                        </p>
                        <button
                          onClick={() => setEditingName(true)}
                          className="btn-icon text-text-muted hover:text-accent-400"
                          title="Edit name"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                ) : saveError ? (
                  <div className="space-y-1">
                    <p className="text-sm text-red-400">{saveError}</p>
                    <button
                      onClick={() => saveToLibrary(result.history_id, result.job_title)}
                      className="text-sm text-accent-400 hover:underline"
                    >
                      Try again
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => saveToLibrary(result.history_id, result.job_title)}
                    className="text-sm text-accent-400 hover:underline flex items-center gap-1"
                  >
                    <Save className="w-4 h-4" />
                    Save to My CVs
                  </button>
                )}
              </div>
              {savedToLibrary && !editingName && (
                <button
                  onClick={removeFromLibrary}
                  className="text-sm text-text-muted hover:text-red-400"
                  title="Remove from library"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-3">
            {(result.cv_pdf_url || result.cv_docx_url) && (
              <div className="relative" ref={downloadMenuRef}>
                <button
                  onClick={() => setShowDownloadMenu(!showDownloadMenu)}
                  className="btn-primary"
                >
                  <Download className="w-5 h-5" />
                  Download
                  <ChevronDown className={`w-4 h-4 ml-1 transition-transform ${showDownloadMenu ? 'rotate-180' : ''}`} />
                </button>
                {showDownloadMenu && (
                  <div className="absolute top-full left-0 mt-2 w-48 rounded-lg bg-surface-elevated border border-border shadow-lg z-10">
                    {result.cv_pdf_url && (
                      <button
                        onClick={() => handleDownload('pdf')}
                        className="w-full px-4 py-2.5 text-left text-sm text-text-primary hover:bg-surface-hover flex items-center gap-2 first:rounded-t-lg"
                      >
                        <FileText className="w-4 h-4 text-red-400" />
                        Download as PDF
                      </button>
                    )}
                    {result.cv_docx_url && (
                      <button
                        onClick={() => handleDownload('docx')}
                        className="w-full px-4 py-2.5 text-left text-sm text-text-primary hover:bg-surface-hover flex items-center gap-2 last:rounded-b-lg"
                      >
                        <FileText className="w-4 h-4 text-blue-400" />
                        Download as Word
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}
            <button onClick={handleCopyMarkdown} className="btn-secondary">
              {copied ? (
                <>
                  <CheckCircle2 className="w-5 h-5" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-5 h-5" />
                  Copy Markdown
                </>
              )}
            </button>
            {/* View Analysis Button */}
            <button
              onClick={() => setShowAnalysisModal(true)}
              disabled={analysisStatus === 'pending' || analysisStatus === 'idle'}
              className={`btn-secondary ${
                analysisStatus === 'ready' ? 'ring-2 ring-accent-500/50' : ''
              }`}
            >
              {analysisStatus === 'pending' ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing...
                </>
              ) : analysisStatus === 'ready' ? (
                <>
                  <BarChart3 className="w-5 h-5" />
                  View Analysis
                  {analysis?.overall_score && (
                    <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded bg-accent-500/20 text-accent-400">
                      {analysis.overall_score}%
                    </span>
                  )}
                </>
              ) : analysisStatus === 'failed' ? (
                <>
                  <AlertCircle className="w-5 h-5" />
                  Analysis Failed
                </>
              ) : (
                <>
                  <BarChart3 className="w-5 h-5" />
                  View Analysis
                </>
              )}
            </button>
            <button
              onClick={() => setShowPreview(!showPreview)}
              className="btn-secondary"
            >
              <Eye className="w-5 h-5" />
              {showPreview ? 'Hide' : 'Show'} Preview
            </button>
            {result.cv_pdf_url && (
              <a
                href={result.cv_pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary"
              >
                <ExternalLink className="w-5 h-5" />
                Open in New Tab
              </a>
            )}
          </div>

          {/* Markdown Preview */}
          {showPreview && result.cv_markdown && (
            <div className="card">
              <h2 className="font-medium text-text-primary mb-4">Generated CV Preview</h2>
              <div className="prose prose-invert max-w-none">
                <pre className="whitespace-pre-wrap text-sm text-text-secondary bg-surface-elevated p-4 rounded-lg overflow-x-auto">
                  {result.cv_markdown}
                </pre>
              </div>
            </div>
          )}
        </div>
      ) : (
        // Input Form
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Left Column - CV Source & Instructions */}
          <div className="space-y-6">
            {/* CV Source Toggle */}
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-medium text-text-primary">Select Your CV</h2>
                <div className="flex items-center gap-2 p-1 rounded-lg bg-surface-elevated">
                  <button
                    onClick={() => {
                      setCvSource('library')
                      setCvFile(null)
                    }}
                    className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                      cvSource === 'library'
                        ? 'bg-accent-500 text-white'
                        : 'text-text-muted hover:text-text-primary'
                    }`}
                  >
                    <FolderOpen className="w-4 h-4 inline mr-1.5" />
                    My Library
                  </button>
                  <button
                    onClick={() => {
                      setCvSource('upload')
                      setSelectedVersion(null)
                    }}
                    className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                      cvSource === 'upload'
                        ? 'bg-accent-500 text-white'
                        : 'text-text-muted hover:text-text-primary'
                    }`}
                  >
                    <Plus className="w-4 h-4 inline mr-1.5" />
                    Upload New
                  </button>
                </div>
              </div>

              {cvSource === 'library' ? (
                // CV Selector from library
                <CVSelector
                  jobDescription={jobDescription}
                  onSelect={handleVersionSelect}
                  onCreateNew={handleCreateNew}
                  selectedVersionId={selectedVersion?.version_id}
                  className="border-0 p-0 bg-transparent"
                />
              ) : (
                // File upload
                <div
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  className={`
                    relative border-2 border-dashed rounded-xl p-8 text-center transition-colors
                    ${
                      dragActive
                        ? 'border-accent-500 bg-accent-500/10'
                        : cvFile
                          ? 'border-emerald-500/50 bg-emerald-500/5'
                          : 'border-border hover:border-text-muted'
                    }
                  `}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                    onChange={handleFileSelect}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />

                  {cvFile ? (
                    <div className="flex items-center justify-center gap-3">
                      <FileText className="w-8 h-8 text-emerald-400" />
                      <div className="text-left">
                        <p className="font-medium text-text-primary">{cvFile.name}</p>
                        <p className="text-sm text-text-muted">
                          {(cvFile.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleRemoveFile()
                        }}
                        className="p-1 hover:bg-surface-elevated rounded-lg transition-colors"
                      >
                        <X className="w-5 h-5 text-text-muted" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <Upload className="w-10 h-10 text-text-muted mx-auto mb-3" />
                      <p className="text-text-primary font-medium">
                        Drop your CV here or click to browse
                      </p>
                      <p className="text-sm text-text-muted mt-1">
                        Supports PDF, DOCX, and TXT files
                      </p>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Special Instructions */}
            <div className="card">
              <h2 className="font-medium text-text-primary mb-4">
                Special Instructions (Optional)
              </h2>
              <textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                className="input min-h-[120px] resize-y"
                placeholder="Add any specific instructions for CV generation...&#10;&#10;Examples:&#10;- Emphasize leadership experience&#10;- Focus on Python and cloud technologies&#10;- Keep it to 2 pages"
              />
            </div>
          </div>

          {/* Right Column - Job Description */}
          <div className="card h-fit">
            <h2 className="font-medium text-text-primary mb-4">Job Description</h2>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              className="input min-h-[300px] resize-y"
              placeholder="Paste the full job description here...&#10;&#10;Include:&#10;- Job title and company&#10;- Required skills and qualifications&#10;- Responsibilities&#10;- Any other relevant details"
            />
            <div className="flex items-center justify-between mt-4 text-sm text-text-muted">
              <span>{jobDescription.length} characters</span>
              {jobDescription.length > 0 && jobDescription.length < 50 && (
                <span className="text-amber-400">Minimum 50 characters required</span>
              )}
            </div>

            {/* Generate Button */}
            <div className="mt-6">
              {error && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm mb-4">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <button
                onClick={handleGenerate}
                disabled={
                  generating ||
                  (cvSource === 'library' ? !selectedVersion : !cvFile) ||
                  jobDescription.length < 50
                }
                className="btn-primary w-full"
              >
                {generating ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Generating your tailored CV...
                  </>
                ) : (
                  <>
                    <FileText className="w-5 h-5" />
                    Generate Tailored CV
                  </>
                )}
              </button>

              {generating && (
                <p className="text-center text-sm text-text-muted mt-3">
                  This may take 30-60 seconds. Please wait...
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Analysis Modal */}
      {showAnalysisModal && analysis && (
        <AnalysisModal
          analysis={analysis}
          onClose={() => setShowAnalysisModal(false)}
        />
      )}
    </div>
  )
}
