import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText,
  Download,
  Search,
  Building2,
  Loader2,
  ExternalLink,
  Eye,
  MapPin,
  Clock,
  ArrowUpDown,
  CheckCircle2,
  Sparkles,
  Briefcase,
} from 'lucide-react'
import { jobService } from '../services/api'

export default function History() {
  const navigate = useNavigate()
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState('date') // 'date' or 'score'

  useEffect(() => {
    loadJobs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortBy])

  const loadJobs = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await jobService.getMatchedJobs(sortBy)
      setJobs(data)
    } catch (err) {
      console.error('Failed to load jobs:', err)
      setError(err.message || 'Failed to load jobs')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateCV = (job) => {
    // Navigate to generate page with job details pre-filled
    navigate('/generate', {
      state: {
        jobTitle: job.job_title,
        jobDescription: job.description,
        jobLink: job.job_link,
        jobId: job.id,
      },
    })
  }

  const handleDownload = async (cvLink, jobTitle) => {
    try {
      // Extract filename from URL or use job title
      const filename = `${jobTitle.replace(/[^a-z0-9]/gi, '_')}_CV.pdf`
      const link = document.createElement('a')
      link.href = cvLink
      link.download = filename
      link.target = '_blank'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      console.error('Failed to download:', err)
    }
  }

  const filteredJobs = jobs.filter(
    (job) =>
      job.job_title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.company?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown'
    try {
      const date = new Date(dateStr)
      const now = new Date()
      const diffMs = now - date
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

      if (diffDays === 0) return 'Today'
      if (diffDays === 1) return 'Yesterday'
      if (diffDays < 7) return `${diffDays} days ago`
      return date.toLocaleDateString('en-AU', { month: 'short', day: 'numeric' })
    } catch {
      return dateStr
    }
  }

  const formatGeneratedDate = (dateStr) => {
    if (!dateStr) return null
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-AU', {
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return null
    }
  }

  // Calculate stats
  const stats = {
    totalMatches: jobs.length,
    withCV: jobs.filter((j) => j.cv_link).length,
    pendingCV: jobs.filter((j) => !j.cv_link).length,
    avgScore: jobs.length
      ? Math.round(jobs.reduce((acc, j) => acc + (j.score || 0), 0) / jobs.length)
      : 0,
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Job Matches</h1>
        <p className="mt-1 text-text-secondary">
          All your matched jobs and their CV generation status
        </p>
      </div>

      {/* Search and Sort */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-10"
            placeholder="Search by job title, company..."
          />
        </div>
        <div className="flex items-center gap-2">
          <ArrowUpDown className="w-4 h-4 text-text-muted" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="input py-2 px-3 min-w-[140px]"
          >
            <option value="date">Newest First</option>
            <option value="score">Highest Match</option>
          </select>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}

      {/* Stats Bar */}
      {!loading && jobs.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="card-elevated text-center py-3">
            <p className="text-xl font-bold text-text-primary">{stats.totalMatches}</p>
            <p className="text-xs text-text-muted">Total Matches</p>
          </div>
          <div className="card-elevated text-center py-3">
            <p className="text-xl font-bold text-emerald-400">{stats.withCV}</p>
            <p className="text-xs text-text-muted">CV Generated</p>
          </div>
          <div className="card-elevated text-center py-3">
            <p className="text-xl font-bold text-amber-400">{stats.pendingCV}</p>
            <p className="text-xs text-text-muted">Pending CV</p>
          </div>
          <div className="card-elevated text-center py-3">
            <p className="text-xl font-bold text-accent-400">{stats.avgScore}%</p>
            <p className="text-xs text-text-muted">Avg Match</p>
          </div>
        </div>
      )}

      {/* Jobs List */}
      <div className="card">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-text-muted animate-spin" />
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="text-center py-12">
            <Briefcase className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-lg font-medium text-text-primary mb-2">
              {searchQuery ? 'No Matches Found' : 'No Job Matches Yet'}
            </h3>
            <p className="text-text-secondary">
              {searchQuery
                ? 'Try adjusting your search'
                : 'Run a job search to find matching opportunities'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filteredJobs.map((job) => (
              <div
                key={job.id}
                className="flex items-start gap-4 py-4 first:pt-0 last:pb-0"
              >
                {/* Company Icon */}
                <div className="w-12 h-12 rounded-xl bg-surface-elevated flex items-center justify-center flex-shrink-0">
                  <Building2 className="w-6 h-6 text-text-muted" />
                </div>

                {/* Job Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-medium text-text-primary truncate">
                      {job.job_title || 'Untitled'}
                    </h3>
                    <span className="badge-primary flex-shrink-0">
                      {Math.round((job.score || 0) * 10)}% match
                    </span>
                  </div>

                  <p className="text-sm text-text-secondary">{job.company}</p>

                  <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-text-muted">
                    {job.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5" />
                        {job.location}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {formatDate(job.posted_date)}
                    </span>
                  </div>

                  {/* CV Status */}
                  <div className="mt-2">
                    {job.cv_link ? (
                      <span className="inline-flex items-center gap-1 text-xs text-emerald-400">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        CV Generated {formatGeneratedDate(job.cv_generated_at) && `on ${formatGeneratedDate(job.cv_generated_at)}`}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs text-amber-400">
                        <Sparkles className="w-3.5 h-3.5" />
                        No CV generated yet
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {job.cv_link ? (
                    <>
                      <a
                        href={job.cv_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-icon text-text-muted hover:text-accent-400"
                        aria-label="View CV"
                        title="View CV"
                      >
                        <Eye className="w-5 h-5" />
                      </a>
                      <button
                        onClick={() => handleDownload(job.cv_link, job.job_title)}
                        className="btn-icon text-text-muted hover:text-accent-400"
                        aria-label="Download CV"
                        title="Download CV"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => handleGenerateCV(job)}
                      className="btn-secondary text-sm py-1.5 px-3"
                      title="Generate tailored CV"
                    >
                      <FileText className="w-4 h-4" />
                      Generate CV
                    </button>
                  )}
                  <a
                    href={job.job_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-icon text-text-muted hover:text-accent-400"
                    aria-label="View job posting"
                    title="View job posting"
                  >
                    <ExternalLink className="w-5 h-5" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
