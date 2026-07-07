// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Lazy import telemetry to avoid circular dependencies
let trackAPIError = null
const getTrackAPIError = () => {
  if (!trackAPIError) {
    import('./telemetry.js').then((module) => {
      trackAPIError = module.trackAPIError
    }).catch(() => {
      // Silently ignore if telemetry module not available
    })
  }
  return trackAPIError
}

// Error codes for categorized error handling
export const ErrorCodes = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  AUTH_EXPIRED: 'AUTH_EXPIRED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
  DOWNLOAD_EXPIRED: 'DOWNLOAD_EXPIRED',
  COOKIE_EXPIRED: 'COOKIE_EXPIRED',
  SCRAPER_FAILED: 'SCRAPER_FAILED',
  UNKNOWN: 'UNKNOWN',
}

// Custom API error with code and user-friendly message
export class ApiError extends Error {
  constructor(message, code = ErrorCodes.UNKNOWN, status = 0, details = null) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }

  // Get user-friendly error message
  get userMessage() {
    switch (this.code) {
      case ErrorCodes.NETWORK_ERROR:
        return 'Unable to connect. Please check your internet connection.'
      case ErrorCodes.AUTH_EXPIRED:
        return 'Your session has expired. Please log in again.'
      case ErrorCodes.FORBIDDEN:
        return 'You do not have permission to perform this action.'
      case ErrorCodes.NOT_FOUND:
        return 'The requested resource was not found.'
      case ErrorCodes.DOWNLOAD_EXPIRED:
        return 'The download link has expired. Please generate a new one.'
      case ErrorCodes.COOKIE_EXPIRED:
        return 'LinkedIn session expired. Please update your cookies in settings.'
      case ErrorCodes.SCRAPER_FAILED:
        return 'Job search failed. LinkedIn may be blocking requests. Try again later.'
      case ErrorCodes.VALIDATION_ERROR:
        return this.message
      case ErrorCodes.SERVER_ERROR:
        return 'Something went wrong on our end. Please try again.'
      default:
        return this.message || 'An unexpected error occurred.'
    }
  }
}

// Get auth headers (token-based auth like sel-exam)
function getAuthHeaders() {
  const token = localStorage.getItem('winningcv_auth_token')
  if (token) {
    return { 'Authorization': `Token ${token}` }
  }
  return {}
}

function formatErrorDetail(detail) {
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (typeof item === 'string') return item
      if (item?.msg) {
        const location = Array.isArray(item.loc) ? item.loc.join('.') : item.loc
        return location ? `${location}: ${item.msg}` : item.msg
      }
      try {
        return JSON.stringify(item)
      } catch {
        return String(item)
      }
    }).join('; ')
  }

  if (detail && typeof detail === 'object') {
    if (detail.msg) return detail.msg
    if (detail.message) return detail.message
    try {
      return JSON.stringify(detail)
    } catch {
      return String(detail)
    }
  }

  return detail ? String(detail) : ''
}

function normalizeApiString(value, fallback = '') {
  if (value === null || value === undefined) return fallback
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (typeof value === 'object') {
    const candidate = value.job_title || value.title || value.name || value.label || value.value || value.id
    return candidate === undefined || candidate === null ? fallback : String(candidate)
  }
  return String(value)
}

function normalizeStringList(value) {
  if (value === null || value === undefined) return []
  const values = Array.isArray(value) ? value : [value]
  return values.map((item) => normalizeApiString(item).trim()).filter(Boolean)
}

// Detect specific error types from response
function categorizeError(status, errorBody) {
  const rawDetail = errorBody?.detail ?? errorBody?.message ?? ''
  const detail = formatErrorDetail(rawDetail)
  const detailLower = detail.toLowerCase()

  // Auth errors
  if (status === 401) {
    return { code: ErrorCodes.AUTH_EXPIRED, message: 'Session expired' }
  }
  if (status === 403) {
    return { code: ErrorCodes.FORBIDDEN, message: 'Access denied' }
  }

  // Not found
  if (status === 404) {
    // Check for expired presigned URLs
    if (detailLower.includes('expired') || detailLower.includes('presigned')) {
      return { code: ErrorCodes.DOWNLOAD_EXPIRED, message: 'Download link expired' }
    }
    return { code: ErrorCodes.NOT_FOUND, message: 'Resource not found' }
  }

  // Validation errors
  if (status === 422 || status === 400) {
    return { code: ErrorCodes.VALIDATION_ERROR, message: detail || 'Invalid input' }
  }

  // Server errors
  if (status >= 500) {
    // Check for LinkedIn/scraper specific errors
    if (detailLower.includes('linkedin') || detailLower.includes('cookie')) {
      if (detailLower.includes('expired') || detailLower.includes('invalid')) {
        return { code: ErrorCodes.COOKIE_EXPIRED, message: 'LinkedIn session expired' }
      }
      return { code: ErrorCodes.SCRAPER_FAILED, message: 'Job search failed' }
    }
    return { code: ErrorCodes.SERVER_ERROR, message: 'Server error' }
  }

  return { code: ErrorCodes.UNKNOWN, message: detail || `Error: ${status}` }
}

// Generic fetch wrapper with improved error handling
async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`

  const defaultHeaders = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(), // Add auth token if available
  }

  // Don't set Content-Type for FormData (let browser set it with boundary)
  const isFormData = options.body instanceof FormData
  if (isFormData) {
    delete defaultHeaders['Content-Type']
  }

  const config = {
    ...options,
    credentials: 'include', // Also include session cookies as fallback
    headers: isFormData
      ? { ...getAuthHeaders(), ...options.headers }
      : {
          ...defaultHeaders,
          ...options.headers,
        },
  }

  try {
    const response = await fetch(url, config)

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}))
      const { code, message } = categorizeError(response.status, errorBody)

      // Dispatch event for auth expiry so AuthContext can handle it
      if (code === ErrorCodes.AUTH_EXPIRED) {
        window.dispatchEvent(new CustomEvent('authExpired', { detail: { endpoint } }))
      }

      // Track API errors for telemetry (skip telemetry endpoint to avoid recursion)
      if (!endpoint.includes('/telemetry')) {
        const track = getTrackAPIError()
        if (track) {
          track(endpoint, response.status, message)
        }
      }

      throw new ApiError(message, code, response.status, errorBody)
    }

    // Handle empty responses
    const text = await response.text()
    return text ? JSON.parse(text) : null
  } catch (error) {
    // Handle network errors (no response at all)
    if (error instanceof TypeError && error.message.includes('fetch')) {
      console.error(`Network Error [${endpoint}]:`, error)
      // Track network error (skip telemetry endpoint)
      if (!endpoint.includes('/telemetry')) {
        const track = getTrackAPIError()
        if (track) {
          track(endpoint, 0, 'Network error')
        }
      }
      throw new ApiError('Network error', ErrorCodes.NETWORK_ERROR, 0)
    }

    // Re-throw ApiError as-is
    if (error instanceof ApiError) {
      console.error(`API Error [${endpoint}]:`, error.code, error.message)
      throw error
    }

    // Wrap unknown errors
    console.error(`API Error [${endpoint}]:`, error)
    throw new ApiError(error.message || 'Unknown error', ErrorCodes.UNKNOWN, 0)
  }
}

// Auth Service - handles authentication
export const authService = {
  // Get current user info
  async getCurrentUser() {
    return fetchAPI('/api/v1/auth/me')
  },

  // Get CSRF token
  async getCSRFToken() {
    return fetchAPI('/api/v1/auth/csrf')
  },

  // Get OAuth login URL
  async getLoginUrl(provider = 'google') {
    return fetchAPI(`/api/v1/auth/login-url?provider=${provider}`)
  },

  // Logout
  async logout() {
    return fetchAPI('/api/v1/auth/logout', { method: 'POST' })
  },
}

// Job Service - handles job matching and search
export const jobService = {
  // Get job search configuration
  async getConfig() {
    return fetchAPI('/api/v1/jobs/config')
  },

  // Save job search configuration
  // cvOption can be: { type: 'file', file: File } or { type: 'version', versionId: string } or null
  async saveConfig(config, cvFile = null, selectedCvVersionId = null) {
    const formData = new FormData()

    // Add config fields
    Object.entries(config).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        formData.append(key, value)
      }
    })

    // Add CV file if provided (upload new CV)
    if (cvFile) {
      formData.append('cv_file', cvFile)
    }
    // Or add selected CV version ID (use from library)
    else if (selectedCvVersionId) {
      formData.append('selected_cv_version_id', selectedCvVersionId)
    }

    return fetchAPI('/api/v1/jobs/config', {
      method: 'POST',
      body: formData,
    })
  },

  // Start job search
  async startSearch() {
    return fetchAPI('/api/v1/jobs/search', {
      method: 'POST',
    })
  },

  // Get search task status
  async getSearchStatus(taskId) {
    return fetchAPI(`/api/v1/jobs/search/${taskId}/status`)
  },

  // Get user's recent/active search tasks (for resumption after page refresh)
  async getActiveTasks(includeCompleted = false) {
    const params = new URLSearchParams()
    if (includeCompleted) params.append('include_completed', 'true')
    return fetchAPI(`/api/v1/jobs/search/tasks?${params.toString()}`)
  },

  // Poll search until complete
  async pollSearchUntilComplete(taskId, onProgress, pollInterval = 2000) {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await this.getSearchStatus(taskId)

          if (onProgress) {
            onProgress(status)
          }

          if (status.status === 'completed') {
            resolve(status)
          } else if (status.status === 'failed') {
            reject(new Error(status.message || 'Search failed'))
          } else {
            // Continue polling
            setTimeout(poll, pollInterval)
          }
        } catch (error) {
          reject(error)
        }
      }

      poll()
    })
  },

  // Get job results with optional sorting
  async getResults(limit = 100, sortBy = 'date') {
    return fetchAPI(`/api/v1/jobs/results?limit=${limit}&sort_by=${sortBy}`)
  },

  // Get matched jobs (alias for results)
  async getMatchedJobs(sortBy = 'date') {
    const response = await this.getResults(100, sortBy)
    return response.items || []
  },

  // Update application tracking status
  async updateApplicationStatus(jobId, applicationStatus, notes = null) {
    return fetchAPI(`/api/v1/jobs/results/${jobId}/application`, {
      method: 'PATCH',
      body: JSON.stringify({
        application_status: applicationStatus,
        application_notes: notes,
      }),
    })
  },

  // Get job statistics
  async getStats() {
    const results = await this.getResults()
    const items = results.items || []

    return {
      totalMatches: items.length,
      cvsGenerated: items.filter((j) => j.cv_link).length,
      avgMatchScore: items.length
        ? Math.round((items.reduce((acc, j) => acc + j.score, 0) / items.length) * 10)
        : 0,
      thisWeek: items.filter((j) => {
        if (!j.posted_date) return false
        const date = new Date(j.posted_date)
        const weekAgo = new Date()
        weekAgo.setDate(weekAgo.getDate() - 7)
        return date > weekAgo
      }).length,
    }
  },
}

// CV Service - handles CV upload and generation
export const cvService = {
  // Upload a new base CV
  async uploadCV(file) {
    const formData = new FormData()
    formData.append('cv_file', file)

    return fetchAPI('/api/v1/cv/upload', {
      method: 'POST',
      body: formData,
    })
  },

  // Generate a tailored CV
  async generateCV(jobDescription, cvFile, instructions = '', useKnowledgeBase = false) {
    const formData = new FormData()
    formData.append('job_description', jobDescription)
    formData.append('cv_file', cvFile)
    if (instructions) {
      formData.append('instructions', instructions)
    }
    if (useKnowledgeBase) {
      formData.append('use_knowledge_base', 'true')
    }

    return fetchAPI('/api/v1/cv/generate', {
      method: 'POST',
      body: formData,
    })
  },

  // Download a generated CV
  async downloadCV(filename) {
    const url = `${API_BASE_URL}/api/v1/cv/download/${filename}`
    const response = await fetch(url, { credentials: 'include' })

    if (!response.ok) {
      throw new Error('Failed to download CV')
    }

    const blob = await response.blob()
    const downloadUrl = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(downloadUrl)
  },

  // Download CV from URL
  downloadFromUrl(url, filename) {
    const a = document.createElement('a')
    a.href = url
    a.download = filename || 'cv.pdf'
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  },

  // Download generated CV through the authenticated API proxy.
  // This avoids browser failures when public /storage presigned URLs are unavailable.
  async downloadGeneratedFile(url, filename, format = 'pdf') {
    const response = await fetch(`${API_BASE_URL}/api/v1/cv/download/generated`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        file_url: url,
        filename: filename || `cv.${format}`,
        format,
      }),
    })

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}))
      const { code, message } = categorizeError(response.status, errorBody)
      throw new ApiError(message, code, response.status, errorBody)
    }

    const blob = await response.blob()
    const downloadUrl = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = filename || `cv.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(downloadUrl)
  },

  // Get CV-JD fit analysis
  async getAnalysis(historyId) {
    return fetchAPI(`/api/v1/cv/analysis/${historyId}`)
  },

  // Regenerate CV with improvements from analysis
  async regenerateWithImprovements(historyId) {
    const formData = new FormData()
    formData.append('history_id', historyId)

    return fetchAPI('/api/v1/cv/regenerate-with-improvements', {
      method: 'POST',
      body: formData,
    })
  },

  // Refine CV with user-provided instructions
  async refineCV(historyId, instructions) {
    const formData = new FormData()
    formData.append("history_id", historyId)
    formData.append("refinement_instructions", instructions)

    return fetchAPI("/api/v1/cv/refine", {
      method: "POST",
      body: formData,
    })
  },
}

// History Service - handles CV history management
export const historyService = {
  // Get CV generation history
  async getHistory(limit = 50) {
    const response = await fetchAPI(`/api/v1/cv/history?limit=${limit}`)
    return response.items || []
  },

  // Download a historical CV
  async downloadCV(pdfUrl, jobTitle) {
    if (pdfUrl) {
      cvService.downloadFromUrl(pdfUrl, `${jobTitle}_cv.pdf`)
    }
  },
}

// Preferences Service - handles user job preferences (via job config)
export const preferencesService = {
  // Get user preferences (from job config)
  async getPreferences() {
    const config = await jobService.getConfig()
    return {
      searchKeywords: config.additional_search_term || '',
      location: config.location || '',
      hoursOld: config.hours_old || 24,
      maxJobs: config.max_jobs_to_scrape || 10,
      country: config.country || 'Australia',
      linkedinUrl: config.linkedin_job_url || '',
      seekUrl: config.seek_job_url || '',
      googleSearchTerm: config.google_search_term || '',
    }
  },

  // Save user preferences (to job config)
  async savePreferences(preferences) {
    return jobService.saveConfig({
      search_keywords: preferences.searchKeywords,
      location: preferences.location,
      hours_old: preferences.hoursOld,
      max_jobs: preferences.maxJobs,
      country: preferences.country,
      search_term: preferences.searchKeywords,
      google_term: preferences.googleSearchTerm,
      seek_category: preferences.seekCategory || 'information-communication-technology',
      seek_salaryrange: preferences.seekSalaryRange || '',
      seek_salarytype: preferences.seekSalaryType || 'annual',
      results_wanted: preferences.resultsWanted || 20,
    })
  },
}

// CV Versions Service - handles CV version management
export const cvVersionsService = {
  // List all CV versions
  async listVersions({ includeArchived = false, category = null, tags = null, limit = 50, offset = 0 } = {}) {
    const params = new URLSearchParams()
    if (includeArchived) params.append('include_archived', 'true')
    if (category) params.append('category', category)
    if (tags) params.append('tags', tags.join(','))
    params.append('limit', limit)
    params.append('offset', offset)

    return fetchAPI(`/api/v1/cv/versions?${params.toString()}`)
  },

  // Get a specific CV version
  async getVersion(versionId, includeUrl = false) {
    const params = includeUrl ? '?include_url=true' : ''
    return fetchAPI(`/api/v1/cv/versions/${versionId}${params}`)
  },

  // Create a new CV version (upload file)
  async createVersion(file, metadata) {
    const formData = new FormData()
    formData.append('cv_file', file)
    formData.append('version_name', metadata.versionName)
    if (metadata.autoCategory) formData.append('auto_category', metadata.autoCategory)
    if (metadata.userTags?.length) formData.append('user_tags', metadata.userTags.join(','))
    if (metadata.sourceJobLink) formData.append('source_job_link', metadata.sourceJobLink)
    if (metadata.sourceJobTitle) formData.append('source_job_title', metadata.sourceJobTitle)
    if (metadata.parentVersionId) formData.append('parent_version_id', metadata.parentVersionId)

    return fetchAPI('/api/v1/cv/versions', {
      method: 'POST',
      body: formData,
    })
  },

  // Update CV version metadata
  async updateVersion(versionId, updates) {
    return fetchAPI(`/api/v1/cv/versions/${versionId}`, {
      method: 'PATCH',
      body: JSON.stringify({
        version_name: updates.versionName,
        auto_category: updates.autoCategory,
        user_tags: updates.userTags,
        is_archived: updates.isArchived,
      }),
    })
  },

  // Archive a CV version
  async archiveVersion(versionId) {
    return fetchAPI(`/api/v1/cv/versions/${versionId}`, {
      method: 'DELETE',
    })
  },

  // Permanently delete a CV version
  async deleteVersion(versionId) {
    return fetchAPI(`/api/v1/cv/versions/${versionId}?permanent=true`, {
      method: 'DELETE',
    })
  },

  // Restore an archived version
  async restoreVersion(versionId) {
    return fetchAPI(`/api/v1/cv/versions/${versionId}/restore`, {
      method: 'POST',
    })
  },

  // Fork a version
  async forkVersion(versionId, newName) {
    return fetchAPI(`/api/v1/cv/versions/${versionId}/fork`, {
      method: 'POST',
      body: JSON.stringify({ new_name: newName }),
    })
  },

  // Get download URL
  async getDownloadUrl(versionId, expiresHours = 1, format = 'pdf') {
    return fetchAPI(`/api/v1/cv/versions/${versionId}/download?expires_hours=${expiresHours}&format=${format}`)
  },

  // Fetch a CV version through the API proxy, preserving the real file type.
  // This avoids feeding an HTML/MinIO error page or a DOCX named cv.pdf into /cv/generate.
  async getVersionFile(versionId, fallbackName = 'cv', format = 'pdf') {
    const response = await fetch(`${API_BASE_URL}/api/v1/cv/versions/${versionId}/file?format=${format}`, {
      credentials: 'include',
      headers: getAuthHeaders(),
    })

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}))
      const { code, message } = categorizeError(response.status, errorBody)
      throw new ApiError(message, code, response.status, errorBody)
    }

    const blob = await response.blob()
    const contentDisposition = response.headers.get('content-disposition') || ''
    const dispositionFilename = contentDisposition.match(/filename="?([^";]+)"?/)?.[1]

    let filename = dispositionFilename || fallbackName || 'cv'
    if (!/\.(pdf|docx|txt)$/i.test(filename)) {
      const extByType = {
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'text/plain': '.txt',
      }
      filename = `${filename}${extByType[blob.type] || ''}`
    }

    return new File([blob], filename, {
      type: blob.type || 'application/octet-stream',
    })
  },

  // Record usage (when CV is applied to job)
  async recordUsage(versionId) {
    return fetchAPI(`/api/v1/cv/versions/${versionId}/use`, {
      method: 'POST',
    })
  },

  // Record response (callback/interview)
  async recordResponse(versionId) {
    return fetchAPI(`/api/v1/cv/versions/${versionId}/response`, {
      method: 'POST',
    })
  },

  // Get matching CV suggestions for a job
  async matchVersions(jobDescription, jobTitle = null, companyName = null, limit = 3) {
    return fetchAPI('/api/v1/cv/versions/match', {
      method: 'POST',
      body: JSON.stringify({
        job_description: jobDescription,
        job_title: jobTitle,
        company_name: companyName,
        limit,
      }),
    })
  },

  // Get analytics summary
  async getAnalytics() {
    return fetchAPI('/api/v1/cv/versions/analytics/summary')
  },

  // Bulk actions
  async bulkAction(versionIds, action) {
    return fetchAPI('/api/v1/cv/versions/bulk', {
      method: 'POST',
      body: JSON.stringify({
        version_ids: versionIds,
        action,
      }),
    })
  },

  // Create a CV version from a history record (save generated CV to library)
  async createFromHistory(historyId, { versionName = null, autoCategory = null, userTags = [] } = {}) {
    const normalizedHistoryId = normalizeApiString(historyId).trim()
    if (!normalizedHistoryId) {
      throw new ApiError('Missing generated CV history reference', ErrorCodes.VALIDATION_ERROR, 0)
    }

    return fetchAPI('/api/v1/cv/versions/from-history', {
      method: 'POST',
      body: JSON.stringify({
        history_id: normalizedHistoryId,
        version_name: versionName === null || versionName === undefined ? null : normalizeApiString(versionName).trim().slice(0, 100),
        auto_category: autoCategory === null || autoCategory === undefined ? null : normalizeApiString(autoCategory).trim().slice(0, 50),
        user_tags: normalizeStringList(userTags),
      }),
    })
  },

  // Get knowledge base statistics
  async getKBStats() {
    return fetchAPI('/api/v1/knowledge-base/stats')
  },

  // Index a CV version into the knowledge base
  async indexVersion(versionId) {
    return fetchAPI('/api/v1/knowledge-base/index', {
      method: 'POST',
      body: JSON.stringify({ cv_version_id: versionId }),
    })
  },

  // Get indexed versions from knowledge base
  async getIndexedVersions() {
    return fetchAPI('/api/v1/knowledge-base/versions')
  },
}

// Profile Service - handles user profile and notification preferences
export const profileService = {
  // Get notification preferences
  async getNotificationPreferences() {
    return fetchAPI('/api/v1/profile/notifications')
  },

  // Update notification preferences
  async updateNotificationPreferences(preferences) {
    return fetchAPI('/api/v1/profile/notifications', {
      method: 'PUT',
      body: JSON.stringify({
        email_alerts: preferences.emailAlerts,
        telegram_alerts: preferences.telegramAlerts,
        wechat_alerts: preferences.wechatAlerts,
        weekly_digest: preferences.weeklyDigest,
        telegram_chat_id: preferences.telegramChatId,
        wechat_id: preferences.wechatId,
        notification_email: preferences.notificationEmail,
      }),
    })
  },

  // Test a notification channel
  async testNotification(channel) {
    return fetchAPI('/api/v1/profile/notifications/test', {
      method: 'POST',
      body: JSON.stringify({ channel }),
    })
  },

  // Update user profile (placeholder - auth service handles this)
  async updateProfile(profile) {
    console.log('Profile update:', profile)
    return { success: true }
  },

  // Export user data (GDPR data portability)
  async exportData() {
    return fetchAPI('/api/v1/profile/export')
  },

  // Delete user account (GDPR right to erasure)
  async deleteAccount() {
    return fetchAPI('/api/v1/profile/account', { method: 'DELETE' })
  },
}

export default {
  authService,
  jobService,
  cvService,
  cvVersionsService,
  historyService,
  preferencesService,
  profileService,
}
