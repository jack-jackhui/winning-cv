export const APPLICATION_STATUSES = [
  { value: 'saved', label: 'Saved' },
  { value: 'cv_generated', label: 'CV generated' },
  { value: 'applied', label: 'Applied' },
  { value: 'interviewing', label: 'Interviewing' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'offer', label: 'Offer' },
  { value: 'archived', label: 'Archived' },
]

const STATUS_VALUES = new Set(APPLICATION_STATUSES.map(({ value }) => value))

function padDatePart(value) {
  return String(value).padStart(2, '0')
}

export function toLocalDateKey(value) {
  if (!value) return ''

  if (typeof value === 'string') {
    const dateOnly = value.match(/^(\d{4})-(\d{2})-(\d{2})(?:$|T)/)
    if (dateOnly && !value.includes('T')) return `${dateOnly[1]}-${dateOnly[2]}-${dateOnly[3]}`
  }

  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())}`
}

export function getFollowUpState(nextActionAt, now = new Date()) {
  const dateKey = toLocalDateKey(nextActionAt)
  if (!dateKey) return null

  const todayKey = toLocalDateKey(now)
  const kind = dateKey < todayKey ? 'overdue' : dateKey === todayKey ? 'today' : 'upcoming'
  const date = new Date(`${dateKey}T00:00:00`)
  const formattedDate = date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() === now.getFullYear() ? undefined : 'numeric',
  })

  return {
    kind,
    dateKey,
    label: kind === 'overdue'
      ? `Overdue · ${formattedDate}`
      : kind === 'today'
        ? 'Due today'
        : `Upcoming · ${formattedDate}`,
  }
}

export function groupApplicationsByStatus(applications) {
  const groups = new Map(APPLICATION_STATUSES.map((status) => [status.value, []]))

  for (const application of applications || []) {
    const status = STATUS_VALUES.has(application?.application_status)
      ? application.application_status
      : 'saved'
    groups.get(status).push(application)
  }

  return APPLICATION_STATUSES.map((status) => ({
    ...status,
    applications: groups.get(status.value),
  })).filter((group) => group.applications.length > 0)
}
