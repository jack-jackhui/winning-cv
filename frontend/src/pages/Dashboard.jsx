import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Briefcase,
  FileText,
  TrendingUp,
  Clock,
  ExternalLink,
  MapPin,
  Building2,
  ChevronRight,
  RefreshCw,
  Search,
  Settings,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { jobService } from '../services/api'

export default function Dashboard() {
  const { user } = useAuth()
  const [jobs, setJobs] = useState([])
  const [stats, setStats] = useState({
    totalMatches: 0,
    cvsGenerated: 0,
    avgMatchScore: 0,
    thisWeek: 0,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [jobsData, statsData] = await Promise.all([
        jobService.getMatchedJobs(),
        jobService.getStats(),
      ])
      setJobs(jobsData)
      setStats(statsData)
    } catch (err) {
      console.error('Failed to load dashboard data:', err)
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const statCards = [
    {
      label: 'Total Matches',
      value: stats.totalMatches,
      icon: Briefcase,
      color: 'text-accent-400',
      bg: 'bg-accent-500/10',
    },
    {
      label: 'CVs Generated',
      value: stats.cvsGenerated,
      icon: FileText,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
    },
    {
      label: 'Avg Match Score',
      value: `${stats.avgMatchScore}%`,
      icon: TrendingUp,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
    },
    {
      label: 'This Week',
      value: stats.thisWeek,
      icon: Clock,
      color: 'text-sky-400',
      bg: 'bg-sky-500/10',
    },
  ]

  const formatPostedDate = (dateStr) => {
    if (!dateStr) return 'Unknown'
    try {
      const date = new Date(dateStr)
      const now = new Date()
      const diffMs = now - date
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

      if (diffDays === 0) return 'Today'
      if (diffDays === 1) return 'Yesterday'
      if (diffDays < 7) return `${diffDays} days ago`
      if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
      return date.toLocaleDateString('en-AU', { month: 'short', day: 'numeric' })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">
            Welcome back, {user?.name?.split(' ')[0] || 'there'}
          </h1>
          <p className="mt-1 text-text-secondary">
            Here&apos;s what&apos;s happening with your job search
          </p>
        </div>
        <button
          onClick={loadDashboardData}
          disabled={loading}
          className="btn-secondary"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <div key={stat.label} className="card flex items-center gap-4">
            <div
              className={`w-12 h-12 rounded-xl ${stat.bg} flex items-center justify-center`}
            >
              <stat.icon className={`w-6 h-6 ${stat.color}`} />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">{stat.value}</p>
              <p className="text-sm text-text-muted">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Matches */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-text-primary">Recent Job Matches</h2>
          <Link to="/history" className="text-sm link flex items-center gap-1">
            View all
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 text-text-muted animate-spin" />
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-12">
            <Briefcase className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-lg font-medium text-text-primary mb-2">No matches yet</h3>
            <p className="text-text-secondary mb-6">
              Configure your job search and run a search to find matching jobs
            </p>
            <Link to="/preferences" className="btn-primary">
              <Settings className="w-5 h-5" />
              Configure Search
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {jobs.slice(0, 5).map((job) => (
              <div
                key={job.id}
                className="flex items-start gap-4 p-4 rounded-xl bg-surface-elevated hover:bg-border/30 transition-colors"
              >
                <div className="w-12 h-12 rounded-xl bg-surface border border-border flex items-center justify-center flex-shrink-0">
                  <Building2 className="w-6 h-6 text-text-muted" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="font-medium text-text-primary truncate">
                        {job.job_title || job.title}
                      </h3>
                      <p className="text-sm text-text-secondary">{job.company}</p>
                    </div>
                    <span className="badge-primary flex-shrink-0">
                      {Math.round(job.score || job.matchScore || 0)}% match
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-sm text-text-muted">
                    {job.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-4 h-4" />
                        {job.location}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {formatPostedDate(job.posted_date || job.postedAt)}
                    </span>
                  </div>
                </div>
                <a
                  href={job.job_link || job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-icon text-text-muted hover:text-text-primary"
                  aria-label="View job"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid sm:grid-cols-3 gap-4">
        <Link
          to="/generate"
          className="card hover:border-accent-500/50 transition-colors group"
        >
          <FileText className="w-8 h-8 text-accent-400 mb-3" />
          <h3 className="font-medium text-text-primary group-hover:text-accent-400 transition-colors">
            Generate CV
          </h3>
          <p className="text-sm text-text-muted mt-1">Create a tailored CV for any job</p>
        </Link>
        <Link
          to="/preferences"
          className="card hover:border-accent-500/50 transition-colors group"
        >
          <Search className="w-8 h-8 text-accent-400 mb-3" />
          <h3 className="font-medium text-text-primary group-hover:text-accent-400 transition-colors">
            Job Search
          </h3>
          <p className="text-sm text-text-muted mt-1">Configure and run job searches</p>
        </Link>
        <Link
          to="/history"
          className="card hover:border-accent-500/50 transition-colors group"
        >
          <Briefcase className="w-8 h-8 text-accent-400 mb-3" />
          <h3 className="font-medium text-text-primary group-hover:text-accent-400 transition-colors">
            Job Matches
          </h3>
          <p className="text-sm text-text-muted mt-1">View all matched jobs and generate CVs</p>
        </Link>
      </div>
    </div>
  )
}
