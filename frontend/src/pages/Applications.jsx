import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  CalendarClock,
  Loader2,
  MapPin,
  RefreshCw,
} from 'lucide-react'
import { jobService } from '../services/api'
import {
  APPLICATION_STATUSES,
  getFollowUpState,
  groupApplicationsByStatus,
  toLocalDateKey,
} from '../utils/applicationPipeline'

const followUpStyles = {
  overdue: 'badge-error',
  today: 'badge-warning',
  upcoming: 'badge-primary',
}

function ApplicationCard({ application, updating, error, onUpdate }) {
  const followUp = getFollowUpState(application.next_action_at)
  const workspacePath = `/applications/${encodeURIComponent(application.id)}`

  return (
    <article className="card-elevated p-4 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <Link to={workspacePath} className="group inline-flex items-center gap-2 font-medium text-text-primary hover:text-accent-400 transition-colors">
            <span className="truncate">{application.job_title || 'Untitled role'}</span>
            <ArrowRight className="w-4 h-4 flex-shrink-0 opacity-0 group-hover:opacity-100" aria-hidden="true" />
          </Link>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-text-secondary">
            <Building2 className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            <span className="truncate">{application.company || 'Company unavailable'}</span>
          </p>
          {application.location && (
            <p className="mt-1 flex items-center gap-1.5 text-xs text-text-muted">
              <MapPin className="w-3.5 h-3.5" aria-hidden="true" />
              <span className="truncate">{application.location}</span>
            </p>
          )}
        </div>
        {followUp && (
          <span className={`${followUpStyles[followUp.kind]} flex-shrink-0`}>
            <CalendarClock className="w-3.5 h-3.5" aria-hidden="true" />
            {followUp.label}
          </span>
        )}
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label htmlFor={`status-${application.id}`} className="input-label">Status</label>
          <select
            id={`status-${application.id}`}
            value={application.application_status || 'saved'}
            onChange={(event) => onUpdate(application, { application_status: event.target.value })}
            className="input py-2 text-sm"
            disabled={updating}
          >
            {APPLICATION_STATUSES.map((status) => (
              <option key={status.value} value={status.value}>{status.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`next-action-${application.id}`} className="input-label">Next action</label>
          <input
            id={`next-action-${application.id}`}
            type="date"
            value={toLocalDateKey(application.next_action_at)}
            onChange={(event) => onUpdate(application, { next_action_at: event.target.value || null })}
            className="input py-2 text-sm"
            disabled={updating}
          />
        </div>
      </div>

      <div className="min-h-5 flex items-center justify-between gap-3">
        {error ? (
          <p role="alert" className="text-xs text-red-400">{error}</p>
        ) : updating ? (
          <p role="status" className="inline-flex items-center gap-1.5 text-xs text-text-muted">
            <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> Saving changes
          </p>
        ) : <span />}
        <Link to={workspacePath} className="link text-sm flex-shrink-0">Open workspace</Link>
      </div>
    </article>
  )
}

export default function Applications() {
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [updatingIds, setUpdatingIds] = useState(() => new Set())
  const [updateErrors, setUpdateErrors] = useState({})

  const loadApplications = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      setApplications(await jobService.getApplications())
    } catch (error) {
      setLoadError(error.userMessage || error.message || 'Failed to load applications.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadApplications()
  }, [loadApplications])

  const handleUpdate = async (application, updates) => {
    const optimisticApplication = { ...application, ...updates }
    setApplications((current) => current.map((item) =>
      item.id === application.id ? optimisticApplication : item
    ))
    setUpdatingIds((current) => new Set(current).add(application.id))
    setUpdateErrors((current) => ({ ...current, [application.id]: null }))

    try {
      const updated = await jobService.updateApplicationStatus(
        application.id,
        optimisticApplication.application_status || 'saved',
        optimisticApplication.application_notes ?? null,
        optimisticApplication.next_action_at || null,
      )
      setApplications((current) => current.map((item) =>
        item.id === application.id ? { ...optimisticApplication, ...updated } : item
      ))
    } catch (error) {
      setApplications((current) => current.map((item) =>
        item.id === application.id ? application : item
      ))
      setUpdateErrors((current) => ({
        ...current,
        [application.id]: error.userMessage || error.message || 'Could not save this application.',
      }))
    } finally {
      setUpdatingIds((current) => {
        const next = new Set(current)
        next.delete(application.id)
        return next
      })
    }
  }

  const groups = groupApplicationsByStatus(applications)

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-text-primary">Applications</h1>
        <p className="mt-1 text-text-secondary">Track every application and keep follow-ups moving.</p>
      </header>

      {loading ? (
        <div className="min-h-[40vh] flex items-center justify-center" role="status">
          <Loader2 className="w-7 h-7 text-accent-400 animate-spin" aria-hidden="true" />
          <span className="sr-only">Loading applications</span>
        </div>
      ) : loadError ? (
        <div className="card border-red-500/30 text-center" role="alert">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto" aria-hidden="true" />
          <h2 className="mt-3 text-lg font-semibold text-text-primary">Applications unavailable</h2>
          <p className="mt-2 text-red-400">{loadError}</p>
          <button type="button" onClick={loadApplications} className="btn-secondary mt-5">
            <RefreshCw className="w-4 h-4" aria-hidden="true" /> Try again
          </button>
        </div>
      ) : groups.length === 0 ? (
        <div className="card text-center py-12">
          <BriefcaseBusiness className="w-12 h-12 text-text-muted mx-auto" aria-hidden="true" />
          <h2 className="mt-4 text-lg font-semibold text-text-primary">No tracked applications yet</h2>
          <p className="mt-2 text-text-secondary">Update a job match to begin tracking it here.</p>
          <Link to="/history" className="btn-secondary mt-5">View job matches</Link>
        </div>
      ) : (
        <div className="space-y-6">
          {groups.map((group) => (
            <section key={group.value} aria-labelledby={`applications-${group.value}`}>
              <div className="mb-3 flex items-center gap-2">
                <h2 id={`applications-${group.value}`} className="text-lg font-semibold text-text-primary">{group.label}</h2>
                <span className="badge bg-surface-elevated text-text-secondary">{group.applications.length}</span>
              </div>
              <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
                {group.applications.map((application) => (
                  <ApplicationCard
                    key={application.id}
                    application={application}
                    updating={updatingIds.has(application.id)}
                    error={updateErrors[application.id]}
                    onUpdate={handleUpdate}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
