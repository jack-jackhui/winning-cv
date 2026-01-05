import { useEffect } from 'react'

/**
 * GitHub OAuth Callback Page for Popup Flow
 *
 * This page is loaded inside the popup window after GitHub OAuth redirect.
 * It extracts the authorization code from the URL and sends it back to the
 * parent window using postMessage.
 */
export default function GitHubCallback() {
  useEffect(() => {
    // Extract code from URL parameters
    const urlParams = new URLSearchParams(window.location.search)
    const code = urlParams.get('code')
    const error = urlParams.get('error')
    const errorDescription = urlParams.get('error_description')

    if (window.opener) {
      // Send message to parent window
      if (code) {
        window.opener.postMessage(
          { type: 'GITHUB_AUTH_SUCCESS', code },
          window.location.origin
        )
      } else if (error) {
        window.opener.postMessage(
          { type: 'GITHUB_AUTH_ERROR', error: errorDescription || error },
          window.location.origin
        )
      } else {
        window.opener.postMessage(
          { type: 'GITHUB_AUTH_ERROR', error: 'No authorization code received' },
          window.location.origin
        )
      }

      // Close popup after a short delay
      setTimeout(() => {
        window.close()
      }, 100)
    } else {
      // If no opener (direct navigation), redirect to login
      window.location.href = '/login'
    }
  }, [])

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-text-secondary">Completing GitHub authentication...</p>
      </div>
    </div>
  )
}
