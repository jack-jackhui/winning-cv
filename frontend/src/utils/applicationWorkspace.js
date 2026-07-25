const TRACKING_STATUSES = new Set(['applied', 'interviewing', 'rejected', 'offer', 'archived'])

export function getSafeExternalUrl(value) {
  if (typeof value !== 'string' || !value.trim()) return null

  try {
    const url = new URL(value)
    if (!['http:', 'https:'].includes(url.protocol)) return null
    if (!url.hostname || url.username || url.password) return null
    return url.href
  } catch {
    return null
  }
}

export function getJobSource(value) {
  const safeUrl = getSafeExternalUrl(value)
  if (!safeUrl) return 'Source unavailable'

  return new URL(safeUrl).hostname.replace(/^www\./, '')
}

export function getWorkflowProgress(job) {
  const status = job?.application_status || 'saved'
  const tailored = Boolean(job?.cv_link) || status === 'cv_generated' || TRACKING_STATUSES.has(status)
  const applied = TRACKING_STATUSES.has(status)

  return {
    analyse: true,
    tailor: tailored,
    apply: applied,
    track: applied,
  }
}

export function formatFitScore(score, scale = 10) {
  if (score == null || Number.isNaN(Number(score))) return 'Unavailable'
  return `${Math.round((Number(score) / scale) * 100)}%`
}
