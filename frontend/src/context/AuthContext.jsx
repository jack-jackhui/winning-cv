import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext(null)

// API base URL for auth endpoints
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const AUTH_SERVICE_URL = import.meta.env.VITE_AUTH_SERVICE_URL || 'https://ai-video-backend.jackhui.com.au'

// Check if Google Identity Services SDK is available
const hasGoogleSDK = () => typeof window !== 'undefined' && window.google?.accounts?.oauth2

// MSAL instance for Microsoft OAuth
let msalInstance = null

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Check authentication status on mount
  const checkAuth = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      // First check for token-based auth (like sel-exam)
      const authToken = localStorage.getItem('winningcv_auth_token')

      if (authToken) {
        // Validate token with auth service
        const response = await fetch(`${AUTH_SERVICE_URL}/api/sehs/user-info/`, {
          method: 'GET',
          headers: {
            'Authorization': `Token ${authToken}`,
            'Content-Type': 'application/json',
          },
        })

        if (response.ok) {
          const data = await response.json()
          setUser({
            id: data.auth_user_id,
            email: data.email,
            name: data.display_name,
            provider: data.provider,
            isVerified: true,
            avatar: data.avatar || null,
            isStaff: data.is_staff,
            isSuperuser: data.is_superuser,
          })
          return
        } else {
          // Token invalid, remove it
          localStorage.removeItem('winningcv_auth_token')
        }
      }

      // Fallback to session-based auth via backend proxy
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const data = await response.json()
        if (data.is_authenticated && data.user) {
          setUser({
            id: data.user.auth_user_id,
            email: data.user.email,
            name: data.user.display_name,
            provider: data.user.provider,
            isVerified: data.user.is_verified,
            avatar: data.user.avatar || null,
          })
        } else {
          setUser(null)
        }
      } else {
        setUser(null)
      }
    } catch (err) {
      console.error('Auth check failed:', err)
      setUser(null)
      setError('Failed to verify authentication')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuth()

    // Listen for OAuth success events (like sel-exam)
    const handleOAuthSuccess = async (event) => {
      const { token } = event.detail
      if (token) {
        localStorage.setItem('winningcv_auth_token', token)
        await checkAuth()
      }
    }

    window.addEventListener('oauthSuccess', handleOAuthSuccess)
    return () => {
      window.removeEventListener('oauthSuccess', handleOAuthSuccess)
    }
  }, [checkAuth])

  // Handle Google OAuth using Google Identity Services SDK (popup flow)
  const handleGoogleLogin = useCallback(() => {
    if (!hasGoogleSDK()) {
      // Fallback to redirect flow
      return false
    }

    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId) {
      console.warn('Google OAuth not configured (missing VITE_GOOGLE_CLIENT_ID)')
      return false
    }

    const client = window.google.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: 'email profile',
      callback: async (response) => {
        if (response.access_token) {
          try {
            // Exchange Google token with auth backend
            const authResponse = await fetch(`${AUTH_SERVICE_URL}/api/dj-rest-auth/google/`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              credentials: 'include',
              body: JSON.stringify({ access_token: response.access_token }),
            })

            if (authResponse.ok) {
              const data = await authResponse.json()
              const { key } = data

              // Store token and trigger auth check
              localStorage.setItem('winningcv_auth_token', key)
              window.dispatchEvent(new CustomEvent('oauthSuccess', { detail: { token: key } }))
            } else {
              throw new Error('Google authentication failed')
            }
          } catch (err) {
            console.error('Google OAuth error:', err)
            setError('Failed to authenticate with Google')
          }
        }
      },
    })
    client.requestAccessToken()
    return true
  }, [])

  // Handle Microsoft OAuth using MSAL popup flow
  const handleMicrosoftLogin = useCallback(async () => {
    const clientId = import.meta.env.VITE_MICROSOFT_CLIENT_ID
    if (!clientId) {
      console.warn('Microsoft OAuth not configured (missing VITE_MICROSOFT_CLIENT_ID)')
      return false
    }

    try {
      // Initialize MSAL instance if not already done
      if (!msalInstance) {
        const { PublicClientApplication } = await import('@azure/msal-browser')

        const redirectUri = window.location.origin.replace(/\/$/, '')
        const msalConfig = {
          auth: {
            clientId: clientId,
            authority: 'https://login.microsoftonline.com/common',
            redirectUri: redirectUri,
            navigateToLoginRequestUrl: false,
          },
          cache: {
            cacheLocation: 'sessionStorage',
            storeAuthStateInCookie: false,
          },
        }

        msalInstance = new PublicClientApplication(msalConfig)
        await msalInstance.initialize()
      }

      // Request configuration for login
      const loginRequest = {
        scopes: ['openid', 'profile', 'email', 'User.Read'],
        prompt: 'select_account',
        redirectUri: window.location.origin.replace(/\/$/, ''),
      }

      // Perform popup login
      const loginResponse = await msalInstance.loginPopup(loginRequest)

      // Acquire access token
      let accessToken = loginResponse.accessToken
      if (!accessToken) {
        const tokenRequest = {
          scopes: ['User.Read'],
          account: loginResponse.account,
        }

        try {
          const tokenResponse = await msalInstance.acquireTokenSilent(tokenRequest)
          accessToken = tokenResponse.accessToken
        } catch {
          const tokenResponse = await msalInstance.acquireTokenPopup(tokenRequest)
          accessToken = tokenResponse.accessToken
        }
      }

      if (accessToken) {
        // Exchange Microsoft token with auth backend
        const authResponse = await fetch(`${AUTH_SERVICE_URL}/api/dj-rest-auth/microsoft/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({ access_token: accessToken }),
        })

        if (authResponse.ok) {
          const data = await authResponse.json()
          const { key } = data

          // Store token and trigger auth check
          localStorage.setItem('winningcv_auth_token', key)
          window.dispatchEvent(new CustomEvent('oauthSuccess', { detail: { token: key } }))
          return true
        } else {
          throw new Error('Microsoft authentication failed')
        }
      }
    } catch (err) {
      // Handle user cancellation gracefully
      if (err.errorCode === 'user_cancelled' || err.message?.includes('user_cancelled')) {
        return true // Silent return, user cancelled
      }
      console.error('Microsoft OAuth error:', err)
      setError('Failed to authenticate with Microsoft')
    }
    return false
  }, [])

  // Handle GitHub OAuth using popup flow
  const handleGitHubLogin = useCallback(() => {
    const clientId = import.meta.env.VITE_GITHUB_CLIENT_ID
    if (!clientId) {
      console.warn('GitHub OAuth not configured (missing VITE_GITHUB_CLIENT_ID)')
      return false
    }

    const redirectUri = `${window.location.origin}/auth/github/callback`
    const scope = 'user:email'
    const state = Date.now().toString()

    const authUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=${scope}&state=${state}`

    // Open popup window for OAuth
    const popup = window.open(authUrl, 'github-login', 'width=500,height=600,scrollbars=yes,resizable=yes')

    // Flag to prevent double-processing (React StrictMode can cause double renders)
    let codeProcessed = false

    // Listen for messages from popup window
    const handleMessage = async (event) => {
      if (event.origin !== window.location.origin) {
        return
      }

      if (event.data?.type === 'GITHUB_AUTH_SUCCESS') {
        // Prevent double-processing of the same code
        if (codeProcessed) {
          console.log('GitHub code already processed, skipping duplicate')
          return
        }
        codeProcessed = true

        const { code } = event.data
        try {
          // Exchange GitHub code with auth backend
          const authResponse = await fetch(`${AUTH_SERVICE_URL}/api/dj-rest-auth/github/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ code }),
          })

          if (authResponse.ok) {
            const data = await authResponse.json()
            const { key } = data

            // Store token and trigger auth check
            localStorage.setItem('winningcv_auth_token', key)
            window.dispatchEvent(new CustomEvent('oauthSuccess', { detail: { token: key } }))
          } else {
            throw new Error('GitHub authentication failed')
          }
        } catch (err) {
          console.error('GitHub OAuth error:', err)
          setError('Failed to authenticate with GitHub')
        }

        if (popup && !popup.closed) {
          popup.close()
        }
        window.removeEventListener('message', handleMessage)
      } else if (event.data?.type === 'GITHUB_AUTH_ERROR') {
        console.error('GitHub auth error:', event.data.error)
        setError('GitHub authentication failed')
        if (popup && !popup.closed) {
          popup.close()
        }
        window.removeEventListener('message', handleMessage)
      }
    }

    window.addEventListener('message', handleMessage)

    // Cleanup if popup closed manually
    const checkClosed = setInterval(() => {
      if (popup?.closed) {
        clearInterval(checkClosed)
        window.removeEventListener('message', handleMessage)
      }
    }, 1000)

    return true
  }, [])

  // Get OAuth login URL from backend (redirect flow)
  const getLoginUrl = async (provider = 'google') => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/auth/login-url?provider=${provider}`,
        {
          method: 'GET',
          credentials: 'include',
        }
      )

      if (response.ok) {
        const data = await response.json()
        return data.login_url
      }
      throw new Error('Failed to get login URL')
    } catch (err) {
      console.error('Failed to get login URL:', err)
      throw err
    }
  }

  // Initiate OAuth login with popup flow (preferred) or redirect fallback
  const loginWithOAuth = async (provider = 'google') => {
    try {
      setError(null)

      // Try popup-based flow first for each provider (better UX, no redirect)
      if (provider === 'google' && handleGoogleLogin()) {
        return
      }

      if (provider === 'microsoft') {
        const success = await handleMicrosoftLogin()
        if (success) return
      }

      if (provider === 'github' && handleGitHubLogin()) {
        return
      }

      // Fallback to redirect-based flow if popup not available
      const oauthUrl = await getLoginUrl(provider)

      // Store the current URL to redirect back after login
      sessionStorage.setItem('auth_return_url', '/dashboard')

      // Redirect to auth service OAuth endpoint
      window.location.href = oauthUrl
    } catch (err) {
      console.error('OAuth login failed:', err)
      setError('Failed to initiate login')
      throw err
    }
  }

  // Handle OAuth callback (called after redirect back from auth service)
  const handleOAuthCallback = useCallback(async () => {
    try {
      setLoading(true)
      // After OAuth redirect, check if we're now authenticated
      await checkAuth()

      // Get stored return URL and redirect
      const returnUrl = sessionStorage.getItem('auth_return_url')
      sessionStorage.removeItem('auth_return_url')

      if (returnUrl && !returnUrl.includes('/login')) {
        window.location.href = returnUrl
      }
    } catch (err) {
      console.error('OAuth callback failed:', err)
      setError('Authentication failed')
    } finally {
      setLoading(false)
    }
  }, [checkAuth])

  // Logout
  const logout = async () => {
    try {
      setLoading(true)

      const authToken = localStorage.getItem('winningcv_auth_token')

      // If we have a token, logout via auth service
      if (authToken) {
        try {
          await fetch(`${AUTH_SERVICE_URL}/api/dj-rest-auth/logout/`, {
            method: 'POST',
            headers: {
              'Authorization': `Token ${authToken}`,
              'Content-Type': 'application/json',
            },
            credentials: 'include',
          })
        } catch (err) {
          console.warn('External logout failed:', err)
        }
        localStorage.removeItem('winningcv_auth_token')
      }

      // Also try session-based logout via backend proxy
      try {
        await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      } catch (err) {
        console.warn('Session logout failed:', err)
      }

      setUser(null)
    } catch (err) {
      console.error('Logout failed:', err)
      // Still clear local user state even if API fails
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  // Refresh authentication status
  const refreshAuth = useCallback(async () => {
    await checkAuth()
  }, [checkAuth])

  // Get CSRF token for forms
  const getCSRFToken = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/csrf`, {
        method: 'GET',
        credentials: 'include',
      })

      if (response.ok) {
        const data = await response.json()
        return data.csrf_token
      }
      return null
    } catch (err) {
      console.error('Failed to get CSRF token:', err)
      return null
    }
  }

  // Get auth token for API calls (if available)
  const getAuthToken = () => {
    return localStorage.getItem('winningcv_auth_token')
  }

  // Get auth headers for API calls
  const getAuthHeaders = () => {
    const token = getAuthToken()
    if (token) {
      return { 'Authorization': `Token ${token}` }
    }
    return {}
  }

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    loginWithOAuth,
    handleOAuthCallback,
    logout,
    refreshAuth,
    getCSRFToken,
    getAuthToken,
    getAuthHeaders,
    authServiceUrl: AUTH_SERVICE_URL,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
