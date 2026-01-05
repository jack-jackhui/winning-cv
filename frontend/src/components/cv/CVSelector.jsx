/**
 * CVSelector - Smart CV version selector for job applications
 *
 * Shows AI-powered suggestions based on job description match,
 * with option to browse all versions or create new.
 */
import { useState, useEffect } from 'react'
import {
  FileText,
  Sparkles,
  Loader2,
  Check,
  TrendingUp,
  FolderOpen,
  Plus,
  Download,
} from 'lucide-react'
import { cvVersionsService } from '../../services/api'

// Match score badge component
function MatchBadge({ score }) {
  let colorClass = 'bg-gray-500/20 text-gray-400'
  if (score >= 80) colorClass = 'bg-green-500/20 text-green-400'
  else if (score >= 60) colorClass = 'bg-yellow-500/20 text-yellow-400'
  else if (score >= 40) colorClass = 'bg-orange-500/20 text-orange-400'

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {score.toFixed(0)}% match
    </span>
  )
}

// Suggestion card component
function SuggestionCard({ suggestion, selected, onSelect, onDownload }) {
  return (
    <div
      onClick={() => onSelect(suggestion)}
      className={`relative p-4 rounded-xl border cursor-pointer transition-all ${
        selected
          ? 'border-accent-500 bg-accent-500/10'
          : 'border-border hover:border-accent-400/50 bg-surface-elevated'
      }`}
    >
      {selected && (
        <div className="absolute top-3 right-3 w-6 h-6 bg-accent-500 rounded-full flex items-center justify-center">
          <Check className="w-4 h-4 text-white" />
        </div>
      )}

      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-surface flex items-center justify-center flex-shrink-0">
          <FileText className="w-5 h-5 text-accent-400" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-medium text-text-primary truncate">{suggestion.version_name}</h4>
            <MatchBadge score={suggestion.overall_score} />
          </div>

          {suggestion.auto_category && (
            <p className="text-sm text-text-secondary mb-2">{suggestion.auto_category}</p>
          )}

          {suggestion.reasons?.length > 0 && (
            <ul className="space-y-1">
              {suggestion.reasons.slice(0, 2).map((reason, i) => (
                <li key={i} className="text-xs text-text-muted flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-accent-400" />
                  {reason}
                </li>
              ))}
            </ul>
          )}

          <div className="flex items-center gap-4 mt-3 text-xs text-text-muted">
            <span className="flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              {suggestion.usage_count} uses
            </span>
            <span>{suggestion.response_rate.toFixed(0)}% response rate</span>
          </div>
        </div>
      </div>

      {selected && suggestion.download_url && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDownload(suggestion)
          }}
          className="mt-3 w-full btn-secondary text-sm"
        >
          <Download className="w-4 h-4 mr-2" />
          Download Selected CV
        </button>
      )}
    </div>
  )
}

// All versions list
function VersionsList({ versions, selected, onSelect, loading }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 text-text-muted animate-spin" />
      </div>
    )
  }

  if (versions.length === 0) {
    return (
      <div className="text-center py-8">
        <FileText className="w-10 h-10 text-text-muted mx-auto mb-2" />
        <p className="text-text-secondary">No CV versions found</p>
      </div>
    )
  }

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">
      {versions.map((version) => (
        <div
          key={version.version_id}
          onClick={() => onSelect(version)}
          className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
            selected?.version_id === version.version_id
              ? 'bg-accent-500/10 border border-accent-500'
              : 'bg-surface-elevated border border-transparent hover:border-border'
          }`}
        >
          <FileText className="w-5 h-5 text-accent-400 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-text-primary truncate">{version.version_name}</p>
            {version.auto_category && (
              <p className="text-xs text-text-muted">{version.auto_category}</p>
            )}
          </div>
          {selected?.version_id === version.version_id && (
            <Check className="w-5 h-5 text-accent-500" />
          )}
        </div>
      ))}
    </div>
  )
}

// Main CVSelector component
export default function CVSelector({
  jobDescription,
  jobTitle,
  companyName,
  onSelect,
  onCreateNew,
  selectedVersionId,
  className = '',
}) {
  const [mode, setMode] = useState('suggestions') // 'suggestions' | 'all'
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const [allVersions, setAllVersions] = useState([])
  const [selected, setSelected] = useState(null)
  const [jobAnalysis, setJobAnalysis] = useState(null)

  // Load suggestions when job description changes
  useEffect(() => {
    if (jobDescription && jobDescription.length >= 50) {
      loadSuggestions()
    }
  }, [jobDescription, jobTitle, companyName])

  // Load all versions when switching to 'all' mode
  useEffect(() => {
    if (mode === 'all' && allVersions.length === 0) {
      loadAllVersions()
    }
  }, [mode])

  // Sync selected with prop
  useEffect(() => {
    if (selectedVersionId && (suggestions.length > 0 || allVersions.length > 0)) {
      const found = [...suggestions, ...allVersions].find(
        (v) => v.version_id === selectedVersionId
      )
      if (found) setSelected(found)
    }
  }, [selectedVersionId, suggestions, allVersions])

  const loadSuggestions = async () => {
    setLoading(true)
    try {
      const result = await cvVersionsService.matchVersions(
        jobDescription,
        jobTitle,
        companyName,
        3
      )
      setSuggestions(result.suggestions || [])
      setJobAnalysis(result.job_analysis || null)
    } catch (err) {
      console.error('Failed to load suggestions:', err)
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }

  const loadAllVersions = async () => {
    setLoading(true)
    try {
      const result = await cvVersionsService.listVersions({ limit: 50 })
      setAllVersions(result.items || [])
    } catch (err) {
      console.error('Failed to load versions:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (version) => {
    setSelected(version)
    onSelect?.(version)
  }

  const handleDownload = async (version) => {
    try {
      const url = version.download_url
      if (url) {
        window.open(url, '_blank')
      } else {
        const { download_url } = await cvVersionsService.getDownloadUrl(version.version_id)
        if (download_url) window.open(download_url, '_blank')
      }
    } catch (err) {
      console.error('Download failed:', err)
    }
  }

  return (
    <div className={`card ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <FolderOpen className="w-5 h-5 text-accent-400" />
          Select CV Version
        </h3>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setMode('suggestions')}
            className={`px-3 py-1 text-sm rounded-lg transition-colors ${
              mode === 'suggestions'
                ? 'bg-accent-500/20 text-accent-400'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Sparkles className="w-4 h-4 inline mr-1" />
            Suggested
          </button>
          <button
            onClick={() => setMode('all')}
            className={`px-3 py-1 text-sm rounded-lg transition-colors ${
              mode === 'all'
                ? 'bg-accent-500/20 text-accent-400'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            All CVs
          </button>
        </div>
      </div>

      {/* Job Analysis Summary */}
      {mode === 'suggestions' && jobAnalysis && (
        <div className="mb-4 p-3 rounded-lg bg-surface-elevated text-sm">
          <p className="text-text-muted">
            Detected role: <span className="text-accent-400">{jobAnalysis.detected_role || 'General'}</span>
            {jobAnalysis.seniority && (
              <> | Level: <span className="text-text-primary">{jobAnalysis.seniority}</span></>
            )}
            {jobAnalysis.all_skills?.length > 0 && (
              <> | Skills: <span className="text-text-secondary">{jobAnalysis.all_skills.slice(0, 3).join(', ')}</span></>
            )}
          </p>
        </div>
      )}

      {/* Content based on mode */}
      {mode === 'suggestions' ? (
        loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 text-text-muted animate-spin mr-2" />
            <span className="text-text-muted">Analyzing job and finding best matches...</span>
          </div>
        ) : suggestions.length > 0 ? (
          <div className="space-y-3">
            {suggestions.map((suggestion) => (
              <SuggestionCard
                key={suggestion.version_id}
                suggestion={suggestion}
                selected={selected?.version_id === suggestion.version_id}
                onSelect={handleSelect}
                onDownload={handleDownload}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <FileText className="w-10 h-10 text-text-muted mx-auto mb-2" />
            <p className="text-text-secondary mb-4">No matching CVs found</p>
            <p className="text-text-muted text-sm mb-4">
              Upload a CV or generate one tailored for this job
            </p>
          </div>
        )
      ) : (
        <VersionsList
          versions={allVersions}
          selected={selected}
          onSelect={handleSelect}
          loading={loading}
        />
      )}

      {/* Actions */}
      <div className="flex gap-3 mt-4 pt-4 border-t border-border">
        <button
          onClick={onCreateNew}
          className="btn-secondary flex-1"
        >
          <Plus className="w-4 h-4 mr-2" />
          Generate New CV
        </button>
        {selected && (
          <button
            onClick={() => handleDownload(selected)}
            className="btn-primary flex-1"
          >
            <Download className="w-4 h-4 mr-2" />
            Use Selected
          </button>
        )}
      </div>
    </div>
  )
}

// Export additional components for use elsewhere
export { MatchBadge, SuggestionCard }
