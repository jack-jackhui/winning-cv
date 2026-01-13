import { useState, useEffect, useCallback } from 'react'
import {
  FileText,
  Download,
  Search,
  Calendar,
  Tag,
  Filter,
  Loader2,
  Plus,
  Archive,
  RotateCcw,
  Trash2,
  Copy,
  MoreVertical,
  Grid3X3,
  List,
  TrendingUp,
  Eye,
  Check,
  X,
  Edit3,
  BarChart3,
  Upload,
  Send,
  MessageCircle,
} from 'lucide-react'
import { cvVersionsService } from '../services/api'

// CV Version Card Component
function CVVersionCard({ version, viewMode, onDownload, onArchive, onRestore, onDelete, onFork, onEdit, onLogApplication, onLogResponse }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [loggingApp, setLoggingApp] = useState(false)
  const [loggingResponse, setLoggingResponse] = useState(false)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      await onDownload(version)
    } finally {
      setDownloading(false)
    }
  }

  const handleLogApplication = async () => {
    setLoggingApp(true)
    try {
      await onLogApplication(version)
    } finally {
      setLoggingApp(false)
    }
  }

  const handleLogResponse = async () => {
    setLoggingResponse(true)
    try {
      await onLogResponse(version)
    } finally {
      setLoggingResponse(false)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown'
    try {
      return new Date(dateStr).toLocaleDateString('en-AU', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return dateStr
    }
  }

  const formatFileSize = (bytes) => {
    if (!bytes) return '-'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const responseRate = version.usage_count > 0
    ? ((version.response_count / version.usage_count) * 100).toFixed(0)
    : 0

  const tags = version.user_tags || []

  if (viewMode === 'list') {
    return (
      <div className={`flex items-center gap-4 py-4 px-4 hover:bg-surface-elevated/50 transition-colors ${version.is_archived ? 'opacity-60' : ''}`}>
        <div className="w-10 h-10 rounded-lg bg-surface-elevated flex items-center justify-center flex-shrink-0">
          <FileText className="w-5 h-5 text-accent-400" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-text-primary truncate">{version.version_name}</h3>
            {version.is_archived && (
              <span className="badge-secondary text-xs">Archived</span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1 text-sm text-text-muted">
            {version.auto_category && (
              <span className="text-accent-400">{version.auto_category}</span>
            )}
            <span>{formatDate(version.created_at)}</span>
            <span>{formatFileSize(version.file_size)}</span>
          </div>
        </div>

        <div className="flex items-center gap-2 text-sm">
          <button
            onClick={handleLogApplication}
            disabled={loggingApp || version.is_archived}
            className="text-center px-3 py-1 rounded-lg hover:bg-surface-elevated transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Click to log application"
          >
            <p className="font-medium text-text-primary">{version.usage_count}</p>
            <p className="text-text-muted text-xs flex items-center gap-1">
              {loggingApp ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
              Uses
            </p>
          </button>
          <button
            onClick={handleLogResponse}
            disabled={loggingResponse || version.is_archived || version.usage_count === 0}
            className="text-center px-3 py-1 rounded-lg hover:bg-surface-elevated transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title={version.usage_count === 0 ? "Log an application first" : "Click to log response"}
          >
            <p className="font-medium text-text-primary">{responseRate}%</p>
            <p className="text-text-muted text-xs flex items-center gap-1">
              {loggingResponse ? <Loader2 className="w-3 h-3 animate-spin" /> : <MessageCircle className="w-3 h-3" />}
              Response
            </p>
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="btn-icon text-text-muted hover:text-accent-400"
            title="Download"
          >
            {downloading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Download className="w-5 h-5" />}
          </button>

          <div className="relative">
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="btn-icon text-text-muted hover:text-text-primary"
            >
              <MoreVertical className="w-5 h-5" />
            </button>

            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 top-full mt-1 w-40 bg-surface-elevated border border-border rounded-lg shadow-lg z-20 py-1">
                  <button
                    onClick={() => { onEdit(version); setMenuOpen(false) }}
                    className="w-full px-4 py-2 text-left text-sm text-text-secondary hover:bg-surface hover:text-text-primary flex items-center gap-2"
                  >
                    <Edit3 className="w-4 h-4" /> Edit
                  </button>
                  <button
                    onClick={() => { onFork(version); setMenuOpen(false) }}
                    className="w-full px-4 py-2 text-left text-sm text-text-secondary hover:bg-surface hover:text-text-primary flex items-center gap-2"
                  >
                    <Copy className="w-4 h-4" /> Fork
                  </button>
                  {version.is_archived ? (
                    <button
                      onClick={() => { onRestore(version); setMenuOpen(false) }}
                      className="w-full px-4 py-2 text-left text-sm text-text-secondary hover:bg-surface hover:text-text-primary flex items-center gap-2"
                    >
                      <RotateCcw className="w-4 h-4" /> Restore
                    </button>
                  ) : (
                    <button
                      onClick={() => { onArchive(version); setMenuOpen(false) }}
                      className="w-full px-4 py-2 text-left text-sm text-text-secondary hover:bg-surface hover:text-text-primary flex items-center gap-2"
                    >
                      <Archive className="w-4 h-4" /> Archive
                    </button>
                  )}
                  <button
                    onClick={() => { onDelete(version); setMenuOpen(false) }}
                    className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" /> Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Grid view
  return (
    <div className={`card hover:border-accent-400/30 transition-all group ${version.is_archived ? 'opacity-60' : ''}`}>
      <div className="flex items-start justify-between mb-4">
        <div className="w-12 h-12 rounded-xl bg-surface-elevated flex items-center justify-center">
          <FileText className="w-6 h-6 text-accent-400" />
        </div>
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="btn-icon text-text-muted hover:text-text-primary opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <MoreVertical className="w-5 h-5" />
          </button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-40 bg-surface-elevated border border-border rounded-lg shadow-lg z-20 py-1">
                <button
                  onClick={() => { onEdit(version); setMenuOpen(false) }}
                  className="w-full px-4 py-2 text-left text-sm text-text-secondary hover:bg-surface hover:text-text-primary flex items-center gap-2"
                >
                  <Edit3 className="w-4 h-4" /> Edit
                </button>
                <button
                  onClick={() => { onFork(version); setMenuOpen(false) }}
                  className="w-full px-4 py-2 text-left text-sm text-text-secondary hover:bg-surface hover:text-text-primary flex items-center gap-2"
                >
                  <Copy className="w-4 h-4" /> Fork
                </button>
                {version.is_archived ? (
                  <button
                    onClick={() => { onRestore(version); setMenuOpen(false) }}
                    className="w-full px-4 py-2 text-left text-sm text-text-secondary hover:bg-surface hover:text-text-primary flex items-center gap-2"
                  >
                    <RotateCcw className="w-4 h-4" /> Restore
                  </button>
                ) : (
                  <button
                    onClick={() => { onArchive(version); setMenuOpen(false) }}
                    className="w-full px-4 py-2 text-left text-sm text-text-secondary hover:bg-surface hover:text-text-primary flex items-center gap-2"
                  >
                    <Archive className="w-4 h-4" /> Archive
                  </button>
                )}
                <button
                  onClick={() => { onDelete(version); setMenuOpen(false) }}
                  className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" /> Delete
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <h3 className="font-medium text-text-primary mb-1 line-clamp-2">{version.version_name}</h3>

      {version.auto_category && (
        <p className="text-sm text-accent-400 mb-2">{version.auto_category}</p>
      )}

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {tags.slice(0, 3).map((tag, i) => (
            <span key={i} className="badge-secondary text-xs">{tag}</span>
          ))}
          {tags.length > 3 && (
            <span className="badge-secondary text-xs">+{tags.length - 3}</span>
          )}
        </div>
      )}

      <div className="flex items-center gap-4 text-sm text-text-muted mb-4">
        <span className="flex items-center gap-1">
          <Calendar className="w-4 h-4" />
          {formatDate(version.created_at)}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4">
        <button
          onClick={handleLogApplication}
          disabled={loggingApp || version.is_archived}
          className="bg-surface-elevated rounded-lg p-2 text-center hover:bg-surface-elevated/80 transition-colors group disabled:opacity-50 disabled:cursor-not-allowed"
          title="Click to log a new application"
        >
          <p className="text-lg font-semibold text-text-primary">{version.usage_count}</p>
          <p className="text-xs text-text-muted flex items-center justify-center gap-1">
            {loggingApp ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />}
            Applications
          </p>
        </button>
        <button
          onClick={handleLogResponse}
          disabled={loggingResponse || version.is_archived || version.usage_count === 0}
          className="bg-surface-elevated rounded-lg p-2 text-center hover:bg-surface-elevated/80 transition-colors group disabled:opacity-50 disabled:cursor-not-allowed"
          title={version.usage_count === 0 ? "Log an application first" : "Click to log a response/interview"}
        >
          <p className="text-lg font-semibold text-text-primary">{responseRate}%</p>
          <p className="text-xs text-text-muted flex items-center justify-center gap-1">
            {loggingResponse ? <Loader2 className="w-3 h-3 animate-spin" /> : <MessageCircle className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />}
            Response Rate
          </p>
        </button>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="btn-secondary flex-1 text-sm"
        >
          {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          Download
        </button>
      </div>

      {version.is_archived && (
        <div className="mt-3 text-center">
          <span className="badge-secondary text-xs">Archived</span>
        </div>
      )}
    </div>
  )
}

// Upload Modal Component
function UploadModal({ isOpen, onClose, onUpload }) {
  const [file, setFile] = useState(null)
  const [versionName, setVersionName] = useState('')
  const [category, setCategory] = useState('')
  const [tags, setTags] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file || !versionName) return

    setUploading(true)
    setError(null)

    try {
      await onUpload(file, {
        versionName,
        autoCategory: category || null,
        userTags: tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : [],
      })
      onClose()
      setFile(null)
      setVersionName('')
      setCategory('')
      setTags('')
    } catch (err) {
      setError(err.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-surface border border-border rounded-2xl w-full max-w-lg p-6 mx-4 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-text-primary">Upload CV Version</h2>
          <button onClick={onClose} className="btn-icon text-text-muted hover:text-text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* File Input */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">CV File</label>
            <div className="border-2 border-dashed border-border rounded-xl p-6 text-center hover:border-accent-400/50 transition-colors">
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="hidden"
                id="cv-upload"
              />
              <label htmlFor="cv-upload" className="cursor-pointer">
                {file ? (
                  <div className="flex items-center justify-center gap-2 text-accent-400">
                    <FileText className="w-5 h-5" />
                    <span>{file.name}</span>
                  </div>
                ) : (
                  <>
                    <Upload className="w-8 h-8 text-text-muted mx-auto mb-2" />
                    <p className="text-text-secondary">Click to upload PDF or DOCX</p>
                  </>
                )}
              </label>
            </div>
          </div>

          {/* Version Name */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">Version Name</label>
            <input
              type="text"
              value={versionName}
              onChange={(e) => setVersionName(e.target.value)}
              className="input"
              placeholder="e.g., Backend Engineer - Python Focus"
              required
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">Category (optional)</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="input"
              placeholder="e.g., Software Engineer"
            />
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">Tags (optional)</label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="input"
              placeholder="python, backend, startup (comma-separated)"
            />
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file || !versionName || uploading}
              className="btn-primary flex-1"
            >
              {uploading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Upload
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Edit Modal Component
function EditModal({ isOpen, version, onClose, onSave }) {
  const [versionName, setVersionName] = useState('')
  const [category, setCategory] = useState('')
  const [tags, setTags] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (version) {
      setVersionName(version.version_name || '')
      setCategory(version.auto_category || '')
      setTags(Array.isArray(version.user_tags) ? version.user_tags.join(', ') : '')
      setError(null)
    }
  }, [version])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!versionName) return

    setSaving(true)
    setError(null)

    try {
      await onSave(version.version_id, {
        versionName,
        autoCategory: category || null,
        userTags: tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : [],
      })
      onClose()
    } catch (err) {
      setError(err.message || 'Failed to update CV version')
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen || !version) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-surface border border-border rounded-2xl w-full max-w-lg p-6 mx-4 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-text-primary">Edit CV Version</h2>
          <button onClick={onClose} className="btn-icon text-text-muted hover:text-text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Version Name */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">Version Name</label>
            <input
              type="text"
              value={versionName}
              onChange={(e) => setVersionName(e.target.value)}
              className="input"
              placeholder="e.g., Backend Engineer - Python Focus"
              required
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">Category (optional)</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="input"
              placeholder="e.g., Software Engineer"
            />
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">Tags (optional)</label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="input"
              placeholder="python, backend, startup (comma-separated)"
            />
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button
              type="submit"
              disabled={!versionName || saving}
              className="btn-primary flex-1"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Check className="w-4 h-4 mr-2" />}
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Fork Modal Component
function ForkModal({ isOpen, version, onClose, onFork }) {
  const [newName, setNewName] = useState('')
  const [forking, setForking] = useState(false)

  useEffect(() => {
    if (version) {
      setNewName(`${version.version_name} (Copy)`)
    }
  }, [version])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!newName) return

    setForking(true)
    try {
      await onFork(version.version_id, newName)
      onClose()
    } finally {
      setForking(false)
    }
  }

  if (!isOpen || !version) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-surface border border-border rounded-2xl w-full max-w-md p-6 mx-4 shadow-xl">
        <h2 className="text-xl font-semibold text-text-primary mb-4">Fork CV Version</h2>
        <p className="text-text-secondary mb-4">
          Create a copy of &ldquo;{version.version_name}&rdquo; that you can modify independently.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">New Version Name</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="input"
              required
            />
          </div>

          <div className="flex gap-3">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button type="submit" disabled={!newName || forking} className="btn-primary flex-1">
              {forking ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
              Fork
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Main CVLibrary Component
export default function CVLibrary() {
  const [versions, setVersions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState('grid')
  const [showArchived, setShowArchived] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState('')
  const [categories, setCategories] = useState([])
  const [allTags, setAllTags] = useState([])
  const [analytics, setAnalytics] = useState(null)

  // Modals
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [forkModalOpen, setForkModalOpen] = useState(false)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState(null)

  const loadVersions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await cvVersionsService.listVersions({
        includeArchived: showArchived,
        category: selectedCategory || null,
      })
      setVersions(data.items || [])
      setCategories(data.categories || [])
      setAllTags(data.tags || [])
    } catch (err) {
      console.error('Failed to load versions:', err)
      setError(err.message || 'Failed to load CV versions')
    } finally {
      setLoading(false)
    }
  }, [showArchived, selectedCategory])

  const loadAnalytics = async () => {
    try {
      const data = await cvVersionsService.getAnalytics()
      setAnalytics(data)
    } catch (err) {
      console.error('Failed to load analytics:', err)
    }
  }

  useEffect(() => {
    loadVersions()
    loadAnalytics()
  }, [loadVersions])

  const handleUpload = async (file, metadata) => {
    await cvVersionsService.createVersion(file, metadata)
    await loadVersions()
    await loadAnalytics()
  }

  const handleDownload = async (version) => {
    try {
      const { download_url } = await cvVersionsService.getDownloadUrl(version.version_id)
      if (download_url) {
        window.open(download_url, '_blank')
      }
    } catch (err) {
      console.error('Download failed:', err)
    }
  }

  const handleArchive = async (version) => {
    try {
      await cvVersionsService.archiveVersion(version.version_id)
      await loadVersions()
    } catch (err) {
      console.error('Archive failed:', err)
    }
  }

  const handleRestore = async (version) => {
    try {
      await cvVersionsService.restoreVersion(version.version_id)
      await loadVersions()
    } catch (err) {
      console.error('Restore failed:', err)
    }
  }

  const handleDelete = async (version) => {
    if (!window.confirm(`Permanently delete "${version.version_name}"? This cannot be undone.`)) return
    try {
      await cvVersionsService.deleteVersion(version.version_id)
      await loadVersions()
      await loadAnalytics()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const handleFork = async (versionId, newName) => {
    await cvVersionsService.forkVersion(versionId, newName)
    await loadVersions()
  }

  const handleEdit = (version) => {
    setSelectedVersion(version)
    setEditModalOpen(true)
  }

  const handleSaveEdit = async (versionId, updates) => {
    await cvVersionsService.updateVersion(versionId, updates)
    await loadVersions()
  }

  const handleLogApplication = async (version) => {
    try {
      await cvVersionsService.recordUsage(version.version_id)
      await loadVersions()
      await loadAnalytics()
    } catch (err) {
      console.error('Failed to log application:', err)
    }
  }

  const handleLogResponse = async (version) => {
    try {
      await cvVersionsService.recordResponse(version.version_id)
      await loadVersions()
      await loadAnalytics()
    } catch (err) {
      console.error('Failed to log response:', err)
    }
  }

  const filteredVersions = versions.filter((v) =>
    v.version_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    v.auto_category?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    v.user_tags?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">My CVs</h1>
          <p className="mt-1 text-text-secondary">
            Manage your CV versions for different roles and applications
          </p>
        </div>
        <button onClick={() => setUploadModalOpen(true)} className="btn-primary">
          <Plus className="w-5 h-5 mr-2" />
          Upload CV
        </button>
      </div>

      {/* Analytics Summary */}
      {analytics && (
        <div className="grid sm:grid-cols-4 gap-4">
          <div className="card-elevated">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-accent-500/10 flex items-center justify-center">
                <FileText className="w-5 h-5 text-accent-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{analytics.active_versions}</p>
                <p className="text-sm text-text-muted">Active CVs</p>
              </div>
            </div>
          </div>
          <div className="card-elevated">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{analytics.total_usage}</p>
                <p className="text-sm text-text-muted">Applications</p>
              </div>
            </div>
          </div>
          <div className="card-elevated">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Check className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{analytics.total_responses}</p>
                <p className="text-sm text-text-muted">Responses</p>
              </div>
            </div>
          </div>
          <div className="card-elevated">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-yellow-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{analytics.overall_response_rate}%</p>
                <p className="text-sm text-text-muted">Response Rate</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-10"
            placeholder="Search CVs..."
          />
        </div>

        <div className="flex gap-2">
          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="input w-auto"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>

          {/* Show Archived Toggle */}
          <button
            onClick={() => setShowArchived(!showArchived)}
            className={`btn-secondary ${showArchived ? 'bg-accent-500/20 border-accent-500/50' : ''}`}
          >
            <Archive className="w-4 h-4 mr-2" />
            {showArchived ? 'Hide Archived' : 'Show Archived'}
          </button>

          {/* View Mode Toggle */}
          <div className="flex border border-border rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 ${viewMode === 'grid' ? 'bg-surface-elevated text-text-primary' : 'text-text-muted hover:text-text-primary'}`}
            >
              <Grid3X3 className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 ${viewMode === 'list' ? 'bg-surface-elevated text-text-primary' : 'text-text-muted hover:text-text-primary'}`}
            >
              <List className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-text-muted animate-spin" />
        </div>
      ) : filteredVersions.length === 0 ? (
        <div className="card text-center py-12">
          <FileText className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary mb-2">No CV Versions Found</h3>
          <p className="text-text-secondary mb-4">
            {searchQuery || selectedCategory
              ? 'Try adjusting your filters'
              : 'Upload your first CV to start building your library'}
          </p>
          {!searchQuery && !selectedCategory && (
            <button onClick={() => setUploadModalOpen(true)} className="btn-primary">
              <Plus className="w-5 h-5 mr-2" />
              Upload Your First CV
            </button>
          )}
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredVersions.map((version) => (
            <CVVersionCard
              key={version.version_id}
              version={version}
              viewMode="grid"
              onDownload={handleDownload}
              onArchive={handleArchive}
              onRestore={handleRestore}
              onDelete={handleDelete}
              onFork={(v) => { setSelectedVersion(v); setForkModalOpen(true) }}
              onEdit={handleEdit}
              onLogApplication={handleLogApplication}
              onLogResponse={handleLogResponse}
            />
          ))}
        </div>
      ) : (
        <div className="card divide-y divide-border">
          {filteredVersions.map((version) => (
            <CVVersionCard
              key={version.version_id}
              version={version}
              viewMode="list"
              onDownload={handleDownload}
              onArchive={handleArchive}
              onRestore={handleRestore}
              onDelete={handleDelete}
              onFork={(v) => { setSelectedVersion(v); setForkModalOpen(true) }}
              onLogApplication={handleLogApplication}
              onLogResponse={handleLogResponse}
              onEdit={handleEdit}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUpload={handleUpload}
      />

      <ForkModal
        isOpen={forkModalOpen}
        version={selectedVersion}
        onClose={() => { setForkModalOpen(false); setSelectedVersion(null) }}
        onFork={handleFork}
      />

      <EditModal
        isOpen={editModalOpen}
        version={selectedVersion}
        onClose={() => { setEditModalOpen(false); setSelectedVersion(null) }}
        onSave={handleSaveEdit}
      />
    </div>
  )
}
