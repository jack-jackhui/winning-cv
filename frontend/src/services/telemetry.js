/**
 * Product Telemetry Client
 *
 * Lightweight client for tracking user events and funnel analytics.
 * Events are batched and sent asynchronously to avoid impacting UX.
 * Failures are silently ignored to never break user flows.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Funnel step mapping for consistent tracking
export const FunnelSteps = {
  SESSION_START: 1,
  CV_UPLOAD: 2,
  PREFERENCES_CONFIGURE: 3,
  JOB_SEARCH_START: 4,
  JOB_SEARCH_COMPLETE: 5,
  JOBS_VIEW: 6,
  JOB_DETAILS_OPEN: 7,
  CV_GENERATE_START: 8,
  CV_GENERATE_COMPLETE: 9,
  CV_PREVIEW: 10,
  CV_REFINE: 11,
  CV_DOWNLOAD: 12,
  CV_SAVE_LIBRARY: 13,
  APPLICATION_STATUS_UPDATE: 14,
}

// Event names for consistent tracking
export const EventNames = {
  // Funnel events
  SESSION_START: 'session_start',
  CV_UPLOAD: 'cv_upload',
  PREFERENCES_CONFIGURE: 'preferences_configure',
  JOB_SEARCH_START: 'job_search_start',
  JOB_SEARCH_COMPLETE: 'job_search_complete',
  JOBS_VIEW: 'jobs_view',
  JOB_DETAILS_OPEN: 'job_details_open',
  CV_GENERATE_START: 'cv_generate_start',
  CV_GENERATE_COMPLETE: 'cv_generate_complete',
  CV_PREVIEW: 'cv_preview',
  CV_REFINE: 'cv_refine',
  CV_DOWNLOAD: 'cv_download',
  CV_SAVE_LIBRARY: 'cv_save_library',
  APPLICATION_STATUS_UPDATE: 'application_status_update',
  // Error events
  SEARCH_EMPTY_RESULTS: 'search_empty_results',
  CV_GENERATION_FAILED: 'cv_generation_failed',
  VALIDATION_ERROR: 'validation_error',
  API_ERROR: 'api_error',
}

// Session management
let sessionId = null

function getSessionId() {
  if (sessionId) return sessionId

  // Try to get from sessionStorage (persists across page reloads but not tabs)
  sessionId = sessionStorage.getItem('telemetry_session_id')

  if (!sessionId) {
    // Generate new session ID
    sessionId = `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`
    sessionStorage.setItem('telemetry_session_id', sessionId)
  }

  return sessionId
}

// Event queue for batching
let eventQueue = []
let flushTimeout = null
const BATCH_SIZE = 10
const FLUSH_INTERVAL_MS = 5000

// Get auth token for API calls
function getAuthHeaders() {
  const token = localStorage.getItem('winningcv_auth_token')
  if (token) {
    return { 'Authorization': `Token ${token}` }
  }
  return {}
}

/**
 * Flush queued events to the server.
 * Runs silently - errors are logged but never thrown.
 */
async function flushEvents() {
  if (eventQueue.length === 0) return

  const events = [...eventQueue]
  eventQueue = []

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/telemetry/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      credentials: 'include',
      body: JSON.stringify({ events }),
    })

    if (!response.ok) {
      console.debug('[Telemetry] Failed to send events:', response.status)
    }
  } catch (error) {
    // Silently ignore errors - telemetry should never break the app
    console.debug('[Telemetry] Error sending events:', error.message)
  }
}

/**
 * Schedule a flush if not already scheduled.
 */
function scheduleFlush() {
  if (flushTimeout) return

  flushTimeout = setTimeout(() => {
    flushTimeout = null
    flushEvents()
  }, FLUSH_INTERVAL_MS)
}

/**
 * Queue an event for sending.
 * Events are batched and sent periodically or when batch size is reached.
 */
function queueEvent(event) {
  const enrichedEvent = {
    ...event,
    session_id: getSessionId(),
    path: window.location.pathname,
    referrer: document.referrer || null,
    client_timestamp: new Date().toISOString(),
  }

  eventQueue.push(enrichedEvent)

  // Flush immediately if batch is full
  if (eventQueue.length >= BATCH_SIZE) {
    if (flushTimeout) {
      clearTimeout(flushTimeout)
      flushTimeout = null
    }
    flushEvents()
  } else {
    scheduleFlush()
  }
}

/**
 * Track a generic event.
 *
 * @param {string} eventName - Event name (use EventNames constants)
 * @param {object} options - Optional event data
 * @param {string} options.entityType - Type of entity (e.g., 'cv', 'job')
 * @param {string} options.entityId - ID of the entity
 * @param {object} options.metadata - Additional context data
 */
export function track(eventName, { entityType, entityId, metadata } = {}) {
  queueEvent({
    event_name: eventName,
    entity_type: entityType || null,
    entity_id: entityId || null,
    metadata: metadata || {},
  })
}

/**
 * Track a funnel step event.
 *
 * @param {string} eventName - Event name (use EventNames constants)
 * @param {object} options - Optional event data
 */
export function trackFunnel(eventName, options = {}) {
  const funnelStep = FunnelSteps[eventName.toUpperCase()] || null

  queueEvent({
    event_name: eventName,
    funnel_step: funnelStep,
    entity_type: options.entityType || null,
    entity_id: options.entityId || null,
    metadata: options.metadata || {},
  })
}

/**
 * Track an error event.
 *
 * @param {string} errorType - Error type (use EventNames error constants)
 * @param {object} details - Error details
 */
export function trackError(errorType, details = {}) {
  queueEvent({
    event_name: errorType,
    metadata: {
      ...details,
      timestamp: new Date().toISOString(),
    },
  })
}

/**
 * Track session start (called on login).
 *
 * @param {object} user - User info
 */
export function trackSessionStart(user = null) {
  trackFunnel(EventNames.SESSION_START, {
    metadata: {
      provider: user?.provider || 'unknown',
      is_new_session: true,
    },
  })
}

/**
 * Track CV upload.
 *
 * @param {string} cvId - CV version ID
 * @param {string} source - Upload source ('upload', 'library')
 */
export function trackCVUpload(cvId, source = 'upload') {
  trackFunnel(EventNames.CV_UPLOAD, {
    entityType: 'cv',
    entityId: cvId,
    metadata: { source },
  })
}

/**
 * Track job search start.
 *
 * @param {string} taskId - Search task ID
 * @param {object} config - Search configuration
 */
export function trackJobSearchStart(taskId, config = {}) {
  trackFunnel(EventNames.JOB_SEARCH_START, {
    entityType: 'search_task',
    entityId: taskId,
    metadata: {
      keywords: config.searchKeywords || null,
      location: config.location || null,
    },
  })
}

/**
 * Track job search completion.
 *
 * @param {string} taskId - Search task ID
 * @param {number} resultsCount - Number of results found
 */
export function trackJobSearchComplete(taskId, resultsCount) {
  trackFunnel(EventNames.JOB_SEARCH_COMPLETE, {
    entityType: 'search_task',
    entityId: taskId,
    metadata: { results_count: resultsCount },
  })

  // Also track if no results (friction point)
  if (resultsCount === 0) {
    trackError(EventNames.SEARCH_EMPTY_RESULTS, {
      task_id: taskId,
    })
  }
}

/**
 * Track CV generation start.
 *
 * @param {string} cvSource - Source CV type ('library', 'upload')
 * @param {boolean} useKnowledgeBase - Whether knowledge base is used
 */
export function trackCVGenerateStart(cvSource, useKnowledgeBase = false) {
  trackFunnel(EventNames.CV_GENERATE_START, {
    metadata: {
      cv_source: cvSource,
      use_knowledge_base: useKnowledgeBase,
    },
  })
}

/**
 * Track CV generation completion.
 *
 * @param {string} historyId - History record ID
 * @param {string} jobTitle - Target job title
 */
export function trackCVGenerateComplete(historyId, jobTitle) {
  trackFunnel(EventNames.CV_GENERATE_COMPLETE, {
    entityType: 'cv_history',
    entityId: historyId,
    metadata: { job_title: jobTitle },
  })
}

/**
 * Track CV generation failure.
 *
 * @param {string} error - Error message
 * @param {string} cvSource - Source CV type
 */
export function trackCVGenerateFailed(error, cvSource = null) {
  trackError(EventNames.CV_GENERATION_FAILED, {
    error: error,
    cv_source: cvSource,
  })
}

/**
 * Track CV download.
 *
 * @param {string} historyId - History record ID
 * @param {string} format - Download format ('pdf', 'docx')
 */
export function trackCVDownload(historyId, format = 'pdf') {
  trackFunnel(EventNames.CV_DOWNLOAD, {
    entityType: 'cv_history',
    entityId: historyId,
    metadata: { format },
  })
}

/**
 * Track CV save to library.
 *
 * @param {string} versionId - New version ID
 * @param {string} historyId - Source history ID
 */
export function trackCVSaveLibrary(versionId, historyId = null) {
  trackFunnel(EventNames.CV_SAVE_LIBRARY, {
    entityType: 'cv_version',
    entityId: versionId,
    metadata: { from_history_id: historyId },
  })
}

/**
 * Track job details view.
 *
 * @param {string} jobId - Job ID
 * @param {string} jobTitle - Job title
 */
export function trackJobDetailsOpen(jobId, jobTitle = null) {
  trackFunnel(EventNames.JOB_DETAILS_OPEN, {
    entityType: 'job',
    entityId: jobId,
    metadata: { job_title: jobTitle },
  })
}

/**
 * Track application status update.
 *
 * @param {string} jobId - Job ID
 * @param {string} status - New status
 */
export function trackApplicationStatusUpdate(jobId, status) {
  trackFunnel(EventNames.APPLICATION_STATUS_UPDATE, {
    entityType: 'job',
    entityId: jobId,
    metadata: { status },
  })
}

/**
 * Track API error for monitoring.
 *
 * @param {string} endpoint - API endpoint
 * @param {number} status - HTTP status code
 * @param {string} message - Error message
 */
export function trackAPIError(endpoint, status, message = null) {
  trackError(EventNames.API_ERROR, {
    endpoint,
    status,
    message,
  })
}

/**
 * Track validation error.
 *
 * @param {string} field - Field that failed validation
 * @param {string} message - Validation message
 */
export function trackValidationError(field, message) {
  trackError(EventNames.VALIDATION_ERROR, {
    field,
    message,
  })
}

// Flush events before page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    if (eventQueue.length > 0) {
      // Use sendBeacon for reliable delivery on page unload
      const payload = JSON.stringify({ events: eventQueue })
      navigator.sendBeacon(
        `${API_BASE_URL}/api/v1/telemetry/events`,
        new Blob([payload], { type: 'application/json' })
      )
    }
  })
}

// Export all for convenience
export default {
  track,
  trackFunnel,
  trackError,
  trackSessionStart,
  trackCVUpload,
  trackJobSearchStart,
  trackJobSearchComplete,
  trackCVGenerateStart,
  trackCVGenerateComplete,
  trackCVGenerateFailed,
  trackCVDownload,
  trackCVSaveLibrary,
  trackJobDetailsOpen,
  trackApplicationStatusUpdate,
  trackAPIError,
  trackValidationError,
  EventNames,
  FunnelSteps,
}
