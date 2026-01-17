import { useState, useEffect, useRef } from 'react'
import {
  Save,
  Loader2,
  CheckCircle2,
  MapPin,
  Search,
  Clock,
  Play,
  AlertCircle,
  Upload,
  FileText,
  X,
  Globe,
  DollarSign,
  ExternalLink,
  FolderOpen,
} from 'lucide-react'
import { jobService, cvService } from '../services/api'
import CVLibraryPicker from '../components/cv/CVLibraryPicker'

const countries = [
  { id: 'Australia', label: 'Australia' },
  { id: 'United States', label: 'United States' },
  { id: 'United Kingdom', label: 'United Kingdom' },
  { id: 'Canada', label: 'Canada' },
  { id: 'Singapore', label: 'Singapore' },
  { id: 'Hong Kong', label: 'Hong Kong' },
]

const locations = {
  Australia: [
    'Greater Sydney',
    'Greater Melbourne',
    'Brisbane',
    'Perth',
    'Adelaide',
    'Canberra',
  ],
  'United States': ['San Francisco', 'New York', 'Los Angeles', 'Seattle', 'Austin', 'Boston'],
  'United Kingdom': ['London', 'Manchester', 'Birmingham', 'Edinburgh', 'Bristol'],
  Canada: ['Toronto', 'Vancouver', 'Montreal', 'Calgary', 'Ottawa'],
  Singapore: ['Singapore'],
  'Hong Kong': ['Hong Kong'],
}

const seekCategories = [
  { id: 'information-communication-technology', label: 'Information & Communication Technology' },
  { id: 'engineering', label: 'Engineering' },
  { id: 'science-technology', label: 'Science & Technology' },
  { id: 'banking-financial-services', label: 'Banking & Financial Services' },
  { id: 'consulting-strategy', label: 'Consulting & Strategy' },
  { id: 'healthcare-medical', label: 'Healthcare & Medical' },
  { id: 'marketing-communications', label: 'Marketing & Communications' },
]

export default function Preferences() {
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Search state
  const [searching, setSearching] = useState(false)
  const [searchStatus, setSearchStatus] = useState(null)

  // CV file state
  const [cvFile, setCvFile] = useState(null)
  const [existingCvUrl, setExistingCvUrl] = useState(null)
  const [selectedCvVersion, setSelectedCvVersion] = useState(null)
  const [showUploadInput, setShowUploadInput] = useState(false)
  const fileInputRef = useRef(null)

  // Config state
  const [config, setConfig] = useState({
    searchKeywords: '',
    location: 'Greater Sydney',
    country: 'Australia',
    hoursOld: 24,
    maxJobs: 10,
    resultsWanted: 20,
    googleSearchTerm: '',
    seekCategory: 'information-communication-technology',
    seekSalaryRange: '',
    seekSalaryType: 'annual',
  })

  // Generated URLs (read-only display)
  const [linkedinUrl, setLinkedinUrl] = useState('')
  const [seekUrl, setSeekUrl] = useState('')

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const data = await jobService.getConfig()
      if (data) {
        setConfig({
          searchKeywords: data.additional_search_term || '',
          location: data.location || 'Greater Sydney',
          country: data.country || 'Australia',
          hoursOld: data.hours_old || 24,
          maxJobs: data.max_jobs_to_scrape || 10,
          resultsWanted: data.results_wanted || 20,
          googleSearchTerm: data.google_search_term || '',
          seekCategory: 'information-communication-technology',
          seekSalaryRange: '',
          seekSalaryType: 'annual',
        })
        setLinkedinUrl(data.linkedin_job_url || '')
        setSeekUrl(data.seek_job_url || '')
        setExistingCvUrl(data.base_cv_link || null)
      }
    } catch (err) {
      console.error('Failed to load config:', err)
      setError('Failed to load configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      const validTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      ]
      if (validTypes.includes(file.type)) {
        setCvFile(file)
        setSelectedCvVersion(null) // Clear library selection when uploading new file
        setError(null)
      } else {
        setError('Please upload a PDF or DOCX file')
      }
    }
  }

  const handleSelectCvVersion = (version) => {
    setSelectedCvVersion(version)
    setCvFile(null) // Clear file upload when selecting from library
    setShowUploadInput(false)
  }

  const handleShowUploadInput = () => {
    setShowUploadInput(true)
    setSelectedCvVersion(null)
  }

  const handleRemoveFile = () => {
    setCvFile(null)
    setShowUploadInput(false)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setSaved(false)
    setError(null)

    try {
      const configData = {
        search_keywords: config.searchKeywords,
        location: config.location,
        country: config.country,
        hours_old: config.hoursOld,
        max_jobs: config.maxJobs,
        results_wanted: config.resultsWanted,
        search_term: config.searchKeywords,
        google_term: config.googleSearchTerm,
        seek_category: config.seekCategory,
        seek_salaryrange: config.seekSalaryRange,
        seek_salarytype: config.seekSalaryType,
      }

      // Pass either uploaded file or selected CV version ID
      const selectedVersionId = selectedCvVersion?.version_id || null
      await jobService.saveConfig(configData, cvFile, selectedVersionId)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)

      // Reset upload states after successful save
      if (cvFile || selectedCvVersion) {
        setCvFile(null)
        setShowUploadInput(false)
        // Keep selectedCvVersion to show what was selected
      }

      // Reload to get updated URLs
      await loadConfig()
    } catch (err) {
      console.error('Failed to save config:', err)
      setError(err.message || 'Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleStartSearch = async () => {
    setSearching(true)
    setSearchStatus({ status: 'pending', message: 'Starting search...', progress: 0 })
    setError(null)

    try {
      // Auto-save config before starting search if there are unsaved CV changes
      if (cvFile || selectedCvVersion) {
        setSearchStatus({ status: 'pending', message: 'Saving configuration...', progress: 5 })
        const configData = {
          search_keywords: config.searchKeywords,
          location: config.location,
          country: config.country,
          hours_old: config.hoursOld,
          max_jobs: config.maxJobs,
          results_wanted: config.resultsWanted,
          search_term: config.searchKeywords,
          google_term: config.googleSearchTerm,
          seek_category: config.seekCategory,
          seek_salaryrange: config.seekSalaryRange,
          seek_salarytype: config.seekSalaryType,
        }
        const selectedVersionId = selectedCvVersion?.version_id || null
        await jobService.saveConfig(configData, cvFile, selectedVersionId)

        // Reset file states after auto-save
        if (cvFile) {
          setCvFile(null)
          setShowUploadInput(false)
        }

        // Reload config to get updated CV URL
        await loadConfig()
      }

      const response = await jobService.startSearch()
      const taskId = response.task_id

      // Poll for status
      await jobService.pollSearchUntilComplete(taskId, (status) => {
        setSearchStatus({
          status: status.status,
          message: status.message,
          progress: status.progress,
          resultsCount: status.results_count,
        })
      })

      setSearchStatus((prev) => ({
        ...prev,
        status: 'completed',
        message: `Search completed! Found ${prev?.resultsCount || 0} matching jobs.`,
      }))
    } catch (err) {
      console.error('Search failed:', err)
      setSearchStatus({
        status: 'failed',
        message: err.message || 'Search failed',
      })
      setError(err.message || 'Job search failed')
    } finally {
      setSearching(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-text-muted animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Job Search Configuration</h1>
        <p className="mt-1 text-text-secondary">
          Configure your job search parameters and run automated searches
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Base CV Selection */}
        <div className="card space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-500/10 flex items-center justify-center">
              <FileText className="w-5 h-5 text-accent-400" />
            </div>
            <div>
              <h2 className="font-medium text-text-primary">Base CV</h2>
              <p className="text-sm text-text-muted">Select a CV from your library or upload a new one</p>
            </div>
          </div>

          {/* Existing CV indicator */}
          {existingCvUrl && !cvFile && !selectedCvVersion && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span className="text-sm text-emerald-400">CV already configured</span>
              <a
                href={existingCvUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto text-sm link flex items-center gap-1"
              >
                View <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx"
            onChange={handleFileSelect}
            className="hidden"
            id="cv-upload"
          />

          {/* Show file upload UI if file selected or upload mode active */}
          {(cvFile || showUploadInput) ? (
            <div className="space-y-3">
              {cvFile ? (
                <div className="flex items-center gap-3 p-4 rounded-xl border border-accent-500 bg-accent-500/5">
                  <FileText className="w-6 h-6 text-accent-400" />
                  <div className="flex-1">
                    <p className="font-medium text-text-primary">{cvFile.name}</p>
                    <p className="text-sm text-text-muted">
                      {(cvFile.size / 1024).toFixed(1)} KB - Ready to upload
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="p-1 hover:bg-surface-elevated rounded-lg"
                  >
                    <X className="w-5 h-5 text-text-muted" />
                  </button>
                </div>
              ) : (
                <label
                  htmlFor="cv-upload"
                  className="flex items-center justify-center gap-3 p-6 rounded-xl border-2 border-dashed border-border hover:border-accent-400 cursor-pointer transition-colors"
                >
                  <Upload className="w-6 h-6 text-text-muted" />
                  <div className="text-center">
                    <p className="text-text-secondary font-medium">Click to select file</p>
                    <p className="text-xs text-text-muted mt-1">PDF or DOCX format</p>
                  </div>
                </label>
              )}
              {!cvFile && (
                <button
                  type="button"
                  onClick={() => setShowUploadInput(false)}
                  className="text-sm text-text-muted hover:text-text-secondary"
                >
                  Cancel and select from library
                </button>
              )}
            </div>
          ) : (
            /* CV Library Picker */
            <CVLibraryPicker
              selectedVersionId={selectedCvVersion?.version_id}
              onSelectVersion={handleSelectCvVersion}
              onUploadNew={handleShowUploadInput}
              existingCvUrl={existingCvUrl}
            />
          )}

          {/* Show selected version info */}
          {selectedCvVersion && !showUploadInput && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-accent-500/10 border border-accent-500/30">
              <FolderOpen className="w-5 h-5 text-accent-400" />
              <div className="flex-1">
                <p className="text-sm font-medium text-text-primary">
                  Selected: {selectedCvVersion.version_name}
                </p>
                {selectedCvVersion.auto_category && (
                  <p className="text-xs text-accent-400">{selectedCvVersion.auto_category}</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Search Keywords */}
        <div className="card space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-500/10 flex items-center justify-center">
              <Search className="w-5 h-5 text-accent-400" />
            </div>
            <div>
              <h2 className="font-medium text-text-primary">Search Keywords</h2>
              <p className="text-sm text-text-muted">Job titles and skills to search for</p>
            </div>
          </div>

          <div>
            <label htmlFor="searchKeywords" className="input-label">
              Search keywords (comma-separated)
            </label>
            <input
              id="searchKeywords"
              type="text"
              value={config.searchKeywords}
              onChange={(e) => setConfig({ ...config, searchKeywords: e.target.value })}
              className="input"
              placeholder="Software Engineer, Python Developer, Full Stack"
            />
          </div>

          <div>
            <label htmlFor="googleSearchTerm" className="input-label">
              Google search term (optional)
            </label>
            <input
              id="googleSearchTerm"
              type="text"
              value={config.googleSearchTerm}
              onChange={(e) => setConfig({ ...config, googleSearchTerm: e.target.value })}
              className="input"
              placeholder="site:linkedin.com software engineer sydney"
            />
          </div>
        </div>

        {/* Location */}
        <div className="card space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-500/10 flex items-center justify-center">
              <MapPin className="w-5 h-5 text-accent-400" />
            </div>
            <div>
              <h2 className="font-medium text-text-primary">Location</h2>
              <p className="text-sm text-text-muted">Where to search for jobs</p>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="country" className="input-label">
                Country
              </label>
              <select
                id="country"
                value={config.country}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    country: e.target.value,
                    location: locations[e.target.value]?.[0] || '',
                  })
                }
                className="input"
              >
                {countries.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="location" className="input-label">
                Location
              </label>
              <select
                id="location"
                value={config.location}
                onChange={(e) => setConfig({ ...config, location: e.target.value })}
                className="input"
              >
                {(locations[config.country] || []).map((loc) => (
                  <option key={loc} value={loc}>
                    {loc}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Search Parameters */}
        <div className="card space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-500/10 flex items-center justify-center">
              <Clock className="w-5 h-5 text-accent-400" />
            </div>
            <div>
              <h2 className="font-medium text-text-primary">Search Parameters</h2>
              <p className="text-sm text-text-muted">Configure search scope</p>
            </div>
          </div>

          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="hoursOld" className="input-label">
                Posted within (hours)
              </label>
              <input
                id="hoursOld"
                type="number"
                min="1"
                max="168"
                value={config.hoursOld}
                onChange={(e) =>
                  setConfig({ ...config, hoursOld: parseInt(e.target.value) || 24 })
                }
                className="input"
              />
            </div>

            <div>
              <label htmlFor="maxJobs" className="input-label">
                Max jobs to scrape
              </label>
              <input
                id="maxJobs"
                type="number"
                min="1"
                max="100"
                value={config.maxJobs}
                onChange={(e) =>
                  setConfig({ ...config, maxJobs: parseInt(e.target.value) || 10 })
                }
                className="input"
              />
            </div>

            <div>
              <label htmlFor="resultsWanted" className="input-label">
                Results per source
              </label>
              <input
                id="resultsWanted"
                type="number"
                min="1"
                max="50"
                value={config.resultsWanted}
                onChange={(e) =>
                  setConfig({ ...config, resultsWanted: parseInt(e.target.value) || 20 })
                }
                className="input"
              />
            </div>
          </div>
        </div>

        {/* SEEK Settings */}
        <div className="card space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-500/10 flex items-center justify-center">
              <Globe className="w-5 h-5 text-accent-400" />
            </div>
            <div>
              <h2 className="font-medium text-text-primary">SEEK Settings</h2>
              <p className="text-sm text-text-muted">Australia-specific search options</p>
            </div>
          </div>

          <div>
            <label htmlFor="seekCategory" className="input-label">
              Job Category
            </label>
            <select
              id="seekCategory"
              value={config.seekCategory}
              onChange={(e) => setConfig({ ...config, seekCategory: e.target.value })}
              className="input"
            >
              {seekCategories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="seekSalaryRange" className="input-label">
                Salary range (e.g., 100000-150000)
              </label>
              <input
                id="seekSalaryRange"
                type="text"
                value={config.seekSalaryRange}
                onChange={(e) => setConfig({ ...config, seekSalaryRange: e.target.value })}
                className="input"
                placeholder="100000-150000"
              />
            </div>

            <div>
              <label htmlFor="seekSalaryType" className="input-label">
                Salary type
              </label>
              <select
                id="seekSalaryType"
                value={config.seekSalaryType}
                onChange={(e) => setConfig({ ...config, seekSalaryType: e.target.value })}
                className="input"
              >
                <option value="annual">Annual</option>
                <option value="hourly">Hourly</option>
              </select>
            </div>
          </div>
        </div>

        {/* Generated URLs (Read-only) */}
        {(linkedinUrl || seekUrl) && (
          <div className="card space-y-4">
            <h2 className="font-medium text-text-primary">Generated Search URLs</h2>

            {linkedinUrl && (
              <div>
                <label className="input-label">LinkedIn URL</label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={linkedinUrl}
                    readOnly
                    className="input flex-1 text-sm bg-surface-elevated"
                  />
                  <a
                    href={linkedinUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-secondary"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              </div>
            )}

            {seekUrl && (
              <div>
                <label className="input-label">SEEK URL</label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={seekUrl}
                    readOnly
                    className="input flex-1 text-sm bg-surface-elevated"
                  />
                  <a
                    href={seekUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-secondary"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-4">
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-5 h-5" />
                Save Configuration
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleStartSearch}
            disabled={searching || saving}
            className="btn-secondary"
          >
            {searching ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Run Job Search
              </>
            )}
          </button>

          {saved && (
            <span className="flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              Configuration saved
            </span>
          )}
        </div>

        {/* Search Status */}
        {searchStatus && (
          <div
            className={`p-4 rounded-xl border ${
              searchStatus.status === 'completed'
                ? 'bg-emerald-500/10 border-emerald-500/20'
                : searchStatus.status === 'failed'
                  ? 'bg-red-500/10 border-red-500/20'
                  : 'bg-accent-500/10 border-accent-500/20'
            }`}
          >
            <div className="flex items-center gap-3">
              {searchStatus.status === 'completed' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              ) : searchStatus.status === 'failed' ? (
                <AlertCircle className="w-5 h-5 text-red-400" />
              ) : (
                <Loader2 className="w-5 h-5 text-accent-400 animate-spin" />
              )}
              <div className="flex-1">
                <p
                  className={`font-medium ${
                    searchStatus.status === 'completed'
                      ? 'text-emerald-400'
                      : searchStatus.status === 'failed'
                        ? 'text-red-400'
                        : 'text-accent-400'
                  }`}
                >
                  {searchStatus.message}
                </p>
                {searchStatus.progress > 0 && searchStatus.status !== 'completed' && (
                  <div className="mt-2 h-2 bg-surface-elevated rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent-500 transition-all duration-300"
                      style={{ width: `${searchStatus.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </form>
    </div>
  )
}
