import { useState, useEffect } from 'react'
import {
  FileText,
  Download,
  Search,
  Calendar,
  Building2,
  Filter,
  Loader2,
  ExternalLink,
  Eye,
  Library,
  CheckCircle2,
  X,
} from 'lucide-react'
import { historyService, cvVersionsService } from '../services/api'

export default function History() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  // Track which items are being saved to library
  const [savingItems, setSavingItems] = useState({}) // { id: 'saving' | 'saved' | 'error' }
  const [savedVersions, setSavedVersions] = useState({}) // { id: version_name }

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await historyService.getHistory()
      setHistory(data)
    } catch (err) {
      console.error('Failed to load history:', err)
      setError(err.message || 'Failed to load history')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async (item) => {
    try {
      await historyService.downloadCV(item.cv_pdf_url, item.job_title)
    } catch (err) {
      console.error('Failed to download:', err)
    }
  }

  const handleSaveToLibrary = async (item) => {
    if (savingItems[item.id]) return

    setSavingItems(prev => ({ ...prev, [item.id]: 'saving' }))

    try {
      const versionName = `${item.job_title} (${formatDate(item.created_at)})`
      const savedVersion = await cvVersionsService.createFromHistory(item.id, {
        versionName,
        autoCategory: 'Generated',
        userTags: ['generated', 'from-history'],
      })

      setSavingItems(prev => ({ ...prev, [item.id]: 'saved' }))
      setSavedVersions(prev => ({ ...prev, [item.id]: savedVersion.version_name }))
    } catch (err) {
      console.error('Failed to save to library:', err)
      setSavingItems(prev => ({ ...prev, [item.id]: 'error' }))
    }
  }

  const filteredHistory = history.filter(
    (item) =>
      item.job_title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.job_description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown date'
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-AU', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">CV Generation History</h1>
        <p className="mt-1 text-text-secondary">
          View and download your previously generated CVs
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="input pl-10"
          placeholder="Search by job title..."
        />
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}

      {/* History List */}
      <div className="card">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-text-muted animate-spin" />
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-lg font-medium text-text-primary mb-2">No CVs Found</h3>
            <p className="text-text-secondary">
              {searchQuery
                ? 'Try adjusting your search'
                : 'Generate your first tailored CV to get started'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filteredHistory.map((item) => (
              <div
                key={item.id}
                className="flex items-start gap-4 py-4 first:pt-0 last:pb-0"
              >
                <div className="w-12 h-12 rounded-xl bg-surface-elevated flex items-center justify-center flex-shrink-0">
                  <FileText className="w-6 h-6 text-accent-400" />
                </div>

                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-text-primary truncate">
                    {item.job_title || 'Untitled'}
                  </h3>

                  {item.job_description && (
                    <p className="text-sm text-text-secondary line-clamp-2 mt-1">
                      {item.job_description.substring(0, 150)}
                      {item.job_description.length > 150 ? '...' : ''}
                    </p>
                  )}

                  <div className="flex items-center gap-4 mt-2 text-sm text-text-muted">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      {formatDate(item.created_at)}
                    </span>
                    {item.instructions && (
                      <span className="badge-secondary text-xs">Has instructions</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {item.cv_pdf_url && (
                    <>
                      {/* Save to Library Button */}
                      {savingItems[item.id] === 'saved' ? (
                        <span className="flex items-center gap-1 text-xs text-emerald-400 px-2">
                          <CheckCircle2 className="w-4 h-4" />
                          Saved
                        </span>
                      ) : savingItems[item.id] === 'saving' ? (
                        <span className="flex items-center gap-1 text-xs text-text-muted px-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                        </span>
                      ) : savingItems[item.id] === 'error' ? (
                        <button
                          onClick={() => handleSaveToLibrary(item)}
                          className="btn-icon text-red-400 hover:text-red-300"
                          aria-label="Retry save to library"
                          title="Failed - click to retry"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleSaveToLibrary(item)}
                          className="btn-icon text-text-muted hover:text-accent-400"
                          aria-label="Save to My CVs"
                          title="Save to My CVs"
                        >
                          <Library className="w-5 h-5" />
                        </button>
                      )}
                      <a
                        href={item.cv_pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-icon text-text-muted hover:text-accent-400"
                        aria-label="View CV"
                      >
                        <Eye className="w-5 h-5" />
                      </a>
                      <button
                        onClick={() => handleDownload(item)}
                        className="btn-icon text-text-muted hover:text-accent-400"
                        aria-label="Download CV"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stats */}
      {!loading && history.length > 0 && (
        <div className="grid sm:grid-cols-3 gap-4">
          <div className="card-elevated text-center">
            <p className="text-2xl font-bold text-text-primary">{history.length}</p>
            <p className="text-sm text-text-muted">Total CVs Generated</p>
          </div>
          <div className="card-elevated text-center">
            <p className="text-2xl font-bold text-text-primary">
              {history.filter((h) => h.cv_pdf_url).length}
            </p>
            <p className="text-sm text-text-muted">Available for Download</p>
          </div>
          <div className="card-elevated text-center">
            <p className="text-2xl font-bold text-text-primary">
              {history.filter((h) => h.instructions).length}
            </p>
            <p className="text-sm text-text-muted">With Custom Instructions</p>
          </div>
        </div>
      )}
    </div>
  )
}
