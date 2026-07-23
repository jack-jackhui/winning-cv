import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Bot,
  Briefcase,
  Building2,
  Check,
  CheckCircle2,
  ClipboardCheck,
  ExternalLink,
  FileText,
  Loader2,
  MapPin,
  SearchCheck,
  Target,
  Users,
} from 'lucide-react'
import { jobService } from '../services/api'
import { trackApplicationStatusUpdate, trackJobDetailsOpen } from '../services/telemetry'
import {
  formatFitScore,
  getJobSource,
  getSafeExternalUrl,
  getWorkflowProgress,
} from '../utils/applicationWorkspace'

const STATUS_OPTIONS = [
  { value: 'saved', label: 'Saved' },
  { value: 'cv_generated', label: 'CV generated' },
  { value: 'applied', label: 'Applied' },
  { value: 'interviewing', label: 'Interviewing' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'offer', label: 'Offer' },
  { value: 'archived', label: 'Archived' },
]

function ScoreCard({ icon: Icon, label, value, colour }) {
  return (
    <div className="card-elevated p-4">
      <div className="flex items-center gap-2 text-sm text-text-secondary">
        <Icon className={`w-4 h-4 ${colour}`} aria-hidden="true" />
        {label}
      </div>
      <p className="mt-2 text-xl font-semibold text-text-primary">{value}</p>
    </div>
  )
}

function StageCard({ number, title, description, complete, children }) {
  return (
    <section className="card-elevated p-5" aria-labelledby={`stage-${number}`}>
      <div className="flex items-start gap-3">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${complete ? 'bg-emerald-500/20 text-emerald-400' : 'bg-accent-500/20 text-accent-400'}`}>
          {complete ? <Check className="w-4 h-4" aria-hidden="true" /> : number}
        </div>
        <div className="min-w-0 flex-1">
          <h2 id={`stage-${number}`} className="font-semibold text-text-primary">{title}</h2>
          <p className="mt-1 text-sm text-text-secondary">{description}</p>
          {children && <div className="mt-4">{children}</div>}
        </div>
      </div>
    </section>
  )
}

export default function ApplicationWorkspace() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [status, setStatus] = useState('saved')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState(null)
  const [trackingUnavailable, setTrackingUnavailable] = useState(false)

  useEffect(() => {
    let active = true

    const loadJob = async () => {
      setLoading(true)
      setLoadError(null)
      try {
        const jobs = await jobService.getMatchedJobs('date')
        const selectedJob = jobs.find((item) => String(item.id) === String(jobId))
        if (!active) return

        setJob(selectedJob || null)
        if (selectedJob) {
          setStatus(selectedJob.application_status || 'saved')
          setNotes(selectedJob.application_notes || '')
          trackJobDetailsOpen(String(selectedJob.id), selectedJob.job_title)
        }
      } catch (error) {
        if (active) setLoadError(error.userMessage || error.message || 'Failed to load this application')
      } finally {
        if (active) setLoading(false)
      }
    }

    loadJob()
    return () => {
      active = false
    }
  }, [jobId])

  const handleTailorCV = () => {
    navigate('/generate', {
      state: {
        jobTitle: job.job_title,
        jobDescription: job.description,
        jobLink: job.job_link,
        jobId: job.id,
      },
    })
  }

  const handleSaveTracking = async () => {
    setSaving(true)
    setSaveMessage(null)
    try {
      const previousStatus = job.application_status || 'saved'
      const updatedJob = await jobService.updateApplicationStatus(job.id, status, notes)
      setJob(updatedJob)
      setStatus(updatedJob.application_status || status)
      setNotes(updatedJob.application_notes || '')
      if (previousStatus !== status) trackApplicationStatusUpdate(String(job.id), status)
      setSaveMessage({ type: 'success', text: 'Application tracking saved.' })
    } catch (error) {
      if (error.status === 501) setTrackingUnavailable(true)
      setSaveMessage({
        type: 'error',
        text: error.status === 501
          ? 'Application tracking is unavailable for the configured storage backend.'
          : error.userMessage || error.message || 'Failed to save application tracking.',
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center" role="status">
        <Loader2 className="w-7 h-7 text-accent-400 animate-spin" aria-hidden="true" />
        <span className="sr-only">Loading application workspace</span>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <button type="button" onClick={() => navigate('/history')} className="btn-ghost">
          <ArrowLeft className="w-4 h-4" aria-hidden="true" /> Back to job matches
        </button>
        <div className="card border-red-500/30" role="alert">
          <h1 className="text-xl font-semibold text-text-primary">Workspace unavailable</h1>
          <p className="mt-2 text-red-400">{loadError}</p>
        </div>
      </div>
    )
  }

  if (!job) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <button type="button" onClick={() => navigate('/history')} className="btn-ghost">
          <ArrowLeft className="w-4 h-4" aria-hidden="true" /> Back to job matches
        </button>
        <div className="card text-center py-12">
          <Briefcase className="w-12 h-12 text-text-muted mx-auto" aria-hidden="true" />
          <h1 className="mt-4 text-xl font-semibold text-text-primary">Application not found</h1>
          <p className="mt-2 text-text-secondary">This job is unavailable or is not in your matched jobs.</p>
        </div>
      </div>
    )
  }

  const applyUrl = getSafeExternalUrl(job.job_link)
  const progress = getWorkflowProgress({ ...job, application_status: status })
  const breakdown = job.score_breakdown

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <button type="button" onClick={() => navigate('/history')} className="btn-ghost -ml-4">
        <ArrowLeft className="w-4 h-4" aria-hidden="true" /> Back to job matches
      </button>

      <header className="card">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-5">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm text-text-muted">
              <Building2 className="w-4 h-4" aria-hidden="true" />
              <span>{job.company || 'Company unavailable'}</span>
              <span aria-hidden="true">·</span>
              <span>{getJobSource(job.job_link)}</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold text-text-primary">{job.job_title || 'Untitled role'}</h1>
            {job.location && (
              <p className="mt-2 flex items-center gap-1.5 text-sm text-text-secondary">
                <MapPin className="w-4 h-4" aria-hidden="true" /> {job.location}
              </p>
            )}
          </div>
          <div className="badge-primary text-sm self-start">
            {formatFitScore(job.score)} match
          </div>
        </div>
      </header>

      <section aria-labelledby="fit-heading" className="space-y-4">
        <div>
          <h2 id="fit-heading" className="text-lg font-semibold text-text-primary">Fit analysis</h2>
          <p className="text-sm text-text-secondary">Existing match signals for this role.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <ScoreCard icon={SearchCheck} label="Overall match" value={formatFitScore(job.score)} colour="text-accent-400" />
          <ScoreCard icon={Target} label="ATS score" value={formatFitScore(breakdown?.ats_score, 100)} colour="text-sky-400" />
          <ScoreCard icon={Users} label="HR score" value={formatFitScore(breakdown?.hr_score, 100)} colour="text-emerald-400" />
          <ScoreCard icon={Bot} label="AI score" value={formatFitScore(breakdown?.llm_score)} colour="text-purple-400" />
        </div>

        {(job.match_reasons?.length > 0 || job.suggestions?.length > 0) ? (
          <div className="grid md:grid-cols-2 gap-4">
            {job.match_reasons?.length > 0 && (
              <div className="card-elevated p-5">
                <h3 className="font-medium text-text-primary">Why this matched</h3>
                <ul className="mt-3 space-y-2 text-sm text-text-secondary list-disc pl-5">
                  {job.match_reasons.map((reason, index) => <li key={`${reason}-${index}`}>{reason}</li>)}
                </ul>
              </div>
            )}
            {job.suggestions?.length > 0 && (
              <div className="card-elevated p-5">
                <h3 className="font-medium text-text-primary">How to improve fit</h3>
                <ul className="mt-3 space-y-2 text-sm text-text-secondary list-disc pl-5">
                  {job.suggestions.map((suggestion, index) => <li key={`${suggestion}-${index}`}>{suggestion}</li>)}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="card-elevated p-5 text-sm text-text-muted">Match explanations are unavailable for this job.</div>
        )}
      </section>

      <section aria-labelledby="workflow-heading" className="space-y-4">
        <div>
          <h2 id="workflow-heading" className="text-lg font-semibold text-text-primary">Application workflow</h2>
          <p className="text-sm text-text-secondary">Move from analysis to a tracked application.</p>
        </div>
        <div className="grid lg:grid-cols-2 gap-4">
          <StageCard number="1" title="Analyse" description="Review the existing fit scores and match explanations." complete={progress.analyse} />

          <StageCard number="2" title="Tailor CV" description={job.cv_link ? 'A tailored CV is available. You can return to the generator to refine it.' : 'Open the existing CV generator with this job context.'} complete={progress.tailor}>
            <button type="button" onClick={handleTailorCV} className="btn-secondary w-full sm:w-auto">
              <FileText className="w-4 h-4" aria-hidden="true" />
              {job.cv_link ? 'Refine tailored CV' : 'Tailor CV'}
            </button>
          </StageCard>

          <StageCard number="3" title="Apply" description="Open the original job posting in a new tab." complete={progress.apply}>
            {applyUrl ? (
              <a href={applyUrl} target="_blank" rel="noopener noreferrer" className="btn-primary w-full sm:w-auto">
                <ExternalLink className="w-4 h-4" aria-hidden="true" /> Apply externally
              </a>
            ) : (
              <p className="text-sm text-amber-400">A safe external application URL is unavailable.</p>
            )}
          </StageCard>

          <StageCard number="4" title="Track" description="Save the current application stage and private notes." complete={progress.track}>
            <div className="space-y-4">
              {trackingUnavailable && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-sm text-amber-400">
                  Tracking updates are not supported by the configured storage backend.
                </div>
              )}
              <div>
                <label htmlFor="application-status" className="input-label">Application status</label>
                <select
                  id="application-status"
                  value={status}
                  onChange={(event) => setStatus(event.target.value)}
                  className="input"
                  disabled={saving || trackingUnavailable}
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <div className="flex items-center justify-between gap-3">
                  <label htmlFor="application-notes" className="input-label">Notes</label>
                  <span className="text-xs text-text-muted">{notes.length}/2000</span>
                </div>
                <textarea
                  id="application-notes"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  className="input min-h-32 resize-y"
                  maxLength={2000}
                  placeholder="Add interview details, follow-up dates, or next steps..."
                  disabled={saving || trackingUnavailable}
                />
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <button
                  type="button"
                  onClick={handleSaveTracking}
                  className="btn-primary"
                  disabled={saving || trackingUnavailable}
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <ClipboardCheck className="w-4 h-4" aria-hidden="true" />}
                  {saving ? 'Saving...' : 'Save tracking'}
                </button>
                {saveMessage && (
                  <p
                    role={saveMessage.type === 'error' ? 'alert' : 'status'}
                    className={`text-sm ${saveMessage.type === 'error' ? 'text-red-400' : 'text-emerald-400'}`}
                  >
                    {saveMessage.type === 'success' && <CheckCircle2 className="inline w-4 h-4 mr-1" aria-hidden="true" />}
                    {saveMessage.text}
                  </p>
                )}
              </div>
            </div>
          </StageCard>
        </div>
      </section>
    </div>
  )
}
