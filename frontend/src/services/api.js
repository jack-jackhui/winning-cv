// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Get auth headers (token-based auth like sel-exam)
function getAuthHeaders() {
  const token = localStorage.getItem('winningcv_auth_token')
  if (token) {
    return { 'Authorization': `Token ${token}` }
  }
  return {}
}

// Generic fetch wrapper with error handling
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
      const error = await response.json().catch(() => ({}))
      const errorMessage = error.detail || error.message || `HTTP error! status: ${response.status}`
      throw new Error(errorMessage)
    }

    // Handle empty responses
    const text = await response.text()
    return text ? JSON.parse(text) : null
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error)
    throw error
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

  // Get job results
  async getResults(limit = 100) {
    return fetchAPI(`/api/v1/jobs/results?limit=${limit}`)
  },

  // Get matched jobs (alias for results)
  async getMatchedJobs() {
    const response = await this.getResults()
    return response.items || []
  },

  // Get job statistics
  async getStats() {
    const results = await this.getResults()
    const items = results.items || []

    return {
      totalMatches: items.length,
      cvsGenerated: items.filter((j) => j.cv_link).length,
      avgMatchScore: items.length
        ? Math.round(items.reduce((acc, j) => acc + j.score, 0) / items.length)
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
  async generateCV(jobDescription, cvFile, instructions = '') {
    const formData = new FormData()
    formData.append('job_description', jobDescription)
    formData.append('cv_file', cvFile)
    if (instructions) {
      formData.append('instructions', instructions)
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

  // Get CV-JD fit analysis
  async getAnalysis(historyId) {
    return fetchAPI(`/api/v1/cv/analysis/${historyId}`)
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
  async getDownloadUrl(versionId, expiresHours = 1) {
    return fetchAPI(`/api/v1/cv/versions/${versionId}/download?expires_hours=${expiresHours}`)
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
        wechat_openid: preferences.wechatOpenId,
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

  // Delete user account (placeholder)
  async deleteAccount() {
    console.log('Delete account requested')
    return { success: true }
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
