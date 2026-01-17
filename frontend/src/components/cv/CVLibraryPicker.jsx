/**
 * CVLibraryPicker - Component for selecting a CV from the user's library
 *
 * Used in the job search preferences page to allow users to either
 * select an existing CV from their library or upload a new one.
 */
import { useState, useEffect } from 'react'
import {
  FileText,
  Loader2,
  Check,
  FolderOpen,
  Upload,
  Calendar,
  ChevronDown,
  X,
} from 'lucide-react'
import { cvVersionsService } from '../../services/api'

// CV Version item in the dropdown
function CVVersionItem({ version, selected, onSelect }) {
  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    try {
      return new Date(dateStr).toLocaleDateString('en-AU', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    } catch {
      return ''
    }
  }

  return (
    <div
      onClick={() => onSelect(version)}
      className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
        selected
          ? 'bg-accent-500/10 border border-accent-500'
          : 'hover:bg-surface-elevated border border-transparent'
      }`}
    >
      <div className="w-9 h-9 rounded-lg bg-surface-elevated flex items-center justify-center flex-shrink-0">
        <FileText className="w-4 h-4 text-accent-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-text-primary truncate text-sm">
          {version.version_name}
        </p>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          {version.auto_category && (
            <span className="text-accent-400">{version.auto_category}</span>
          )}
          {version.created_at && (
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {formatDate(version.created_at)}
            </span>
          )}
        </div>
      </div>
      {selected && <Check className="w-4 h-4 text-accent-500 flex-shrink-0" />}
    </div>
  )
}

export default function CVLibraryPicker({
  selectedVersionId,
  onSelectVersion,
  onUploadNew,
  existingCvUrl,
  className = '',
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [versions, setVersions] = useState([])
  const [selectedVersion, setSelectedVersion] = useState(null)

  // Load CV versions from library
  useEffect(() => {
    loadVersions()
  }, [])

  // Sync selected version when selectedVersionId changes
  useEffect(() => {
    if (selectedVersionId && versions.length > 0) {
      const found = versions.find((v) => v.version_id === selectedVersionId)
      if (found) setSelectedVersion(found)
    } else if (!selectedVersionId) {
      setSelectedVersion(null)
    }
  }, [selectedVersionId, versions])

  const loadVersions = async () => {
    setLoading(true)
    try {
      const result = await cvVersionsService.listVersions({
        includeArchived: false,
        limit: 50,
      })
      setVersions(result.items || [])
    } catch (err) {
      console.error('Failed to load CV versions:', err)
      setVersions([])
    } finally {
      setLoading(false)
    }
  }

  const handleSelectVersion = (version) => {
    setSelectedVersion(version)
    onSelectVersion?.(version)
    setIsOpen(false)
  }

  const handleClearSelection = (e) => {
    e.stopPropagation()
    setSelectedVersion(null)
    onSelectVersion?.(null)
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Selected CV display / Dropdown trigger */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-colors text-left ${
            isOpen
              ? 'border-accent-500 bg-surface-elevated'
              : 'border-border hover:border-text-muted bg-surface'
          }`}
        >
          <div className="w-10 h-10 rounded-lg bg-surface-elevated flex items-center justify-center flex-shrink-0">
            <FolderOpen className="w-5 h-5 text-accent-400" />
          </div>

          <div className="flex-1 min-w-0">
            {selectedVersion ? (
              <>
                <p className="font-medium text-text-primary truncate">
                  {selectedVersion.version_name}
                </p>
                <p className="text-sm text-accent-400">
                  {selectedVersion.auto_category || 'From My CVs'}
                </p>
              </>
            ) : (
              <>
                <p className="font-medium text-text-secondary">
                  Select from My CVs
                </p>
                <p className="text-sm text-text-muted">
                  Choose an existing CV from your library
                </p>
              </>
            )}
          </div>

          {selectedVersion ? (
            <button
              type="button"
              onClick={handleClearSelection}
              className="p-1 hover:bg-surface rounded-lg"
            >
              <X className="w-4 h-4 text-text-muted" />
            </button>
          ) : (
            <ChevronDown
              className={`w-5 h-5 text-text-muted transition-transform ${
                isOpen ? 'rotate-180' : ''
              }`}
            />
          )}
        </button>

        {/* Dropdown */}
        {isOpen && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setIsOpen(false)}
            />
            <div className="absolute left-0 right-0 top-full mt-2 bg-surface border border-border rounded-xl shadow-lg z-20 max-h-72 overflow-hidden">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 text-text-muted animate-spin" />
                </div>
              ) : versions.length === 0 ? (
                <div className="p-4 text-center">
                  <FileText className="w-8 h-8 text-text-muted mx-auto mb-2" />
                  <p className="text-sm text-text-secondary">No CVs in library</p>
                  <p className="text-xs text-text-muted mt-1">
                    Upload a CV to your library first
                  </p>
                </div>
              ) : (
                <div className="p-2 space-y-1 overflow-y-auto max-h-64">
                  {versions.map((version) => (
                    <CVVersionItem
                      key={version.version_id}
                      version={version}
                      selected={selectedVersion?.version_id === version.version_id}
                      onSelect={handleSelectVersion}
                    />
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Divider with "or" */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-border" />
        <span className="text-sm text-text-muted">or</span>
        <div className="flex-1 h-px bg-border" />
      </div>

      {/* Upload new option */}
      <button
        type="button"
        onClick={onUploadNew}
        className="w-full flex items-center justify-center gap-2 p-3 rounded-xl border-2 border-dashed border-border hover:border-text-muted transition-colors"
      >
        <Upload className="w-5 h-5 text-text-muted" />
        <span className="text-text-secondary">Upload a new CV</span>
      </button>

      {/* Show existing CV link if available and no version selected */}
      {existingCvUrl && !selectedVersion && (
        <div className="flex items-center gap-2 p-2 rounded-lg bg-emerald-500/10 text-sm">
          <Check className="w-4 h-4 text-emerald-400" />
          <span className="text-emerald-400">Current CV already uploaded</span>
        </div>
      )}
    </div>
  )
}
