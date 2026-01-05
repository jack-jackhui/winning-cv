import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Loader2, CheckCircle, XCircle, FileText } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function AuthCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { handleOAuthCallback, refreshAuth } = useAuth()
  const [status, setStatus] = useState('processing') // 'processing', 'success', 'error'
  const [message, setMessage] = useState('')

  useEffect(() => {
    const processCallback = async () => {
      try {
        // Check for errors from OAuth provider
        const error = searchParams.get('error')
        const errorDescription = searchParams.get('error_description')

        if (error) {
          setStatus('error')
          setMessage(errorDescription || error || 'Authentication failed')
          return
        }

        // After OAuth redirect, the auth service should have set session cookies
        // We just need to verify the authentication status
        await refreshAuth()

        setStatus('success')
        setMessage('Authentication successful! Redirecting...')

        // Get return URL or default to dashboard
        const returnUrl = sessionStorage.getItem('auth_return_url') || '/dashboard'
        sessionStorage.removeItem('auth_return_url')

        // Redirect after a short delay
        setTimeout(() => {
          navigate(returnUrl, { replace: true })
        }, 1500)
      } catch (error) {
        setStatus('error')
        setMessage(error.message || 'An unexpected error occurred')
      }
    }

    processCallback()
  }, [searchParams, handleOAuthCallback, refreshAuth, navigate])

  const handleReturnToLogin = () => {
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        {/* Logo */}
        <div className="mb-8">
          <div className="w-16 h-16 bg-accent-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <FileText className="w-8 h-8 text-white" />
          </div>
        </div>

        {/* Status Card */}
        <div className="card p-8">
          {status === 'processing' && (
            <div className="space-y-6">
              <Loader2 className="w-16 h-16 text-accent-500 mx-auto animate-spin" />
              <div>
                <h2 className="text-xl font-semibold text-text-primary mb-2">
                  Completing Sign In
                </h2>
                <p className="text-text-secondary">
                  Please wait while we verify your authentication...
                </p>
              </div>
            </div>
          )}

          {status === 'success' && (
            <div className="space-y-6">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto" />
              <div>
                <h2 className="text-xl font-semibold text-text-primary mb-2">
                  Welcome to WinningCV!
                </h2>
                <p className="text-text-secondary">{message}</p>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="space-y-6">
              <XCircle className="w-16 h-16 text-red-500 mx-auto" />
              <div>
                <h2 className="text-xl font-semibold text-text-primary mb-2">
                  Sign In Failed
                </h2>
                <p className="text-text-secondary mb-4">{message}</p>
                <button onClick={handleReturnToLogin} className="btn-primary">
                  Return to Login
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <p className="mt-8 text-xs text-text-muted">
          Secure authentication powered by your trusted identity provider
        </p>
      </div>
    </div>
  )
}
