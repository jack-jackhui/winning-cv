import { Link } from 'react-router-dom'
import { FileText, ArrowRight } from 'lucide-react'

export default function Signup() {
  return (
    <div className="min-h-[calc(100vh-5rem)] flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-md text-center">
        {/* Header */}
        <div className="mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-6">
            <div className="w-10 h-10 bg-accent-600 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
          </Link>
          <h1 className="text-2xl font-bold text-text-primary">
            Get Started with WinningCV
          </h1>
          <p className="mt-2 text-text-secondary">
            Create your account using Google, Microsoft, or GitHub
          </p>
        </div>

        {/* Info Card */}
        <div className="card mb-8">
          <div className="space-y-4 text-left">
            <h2 className="font-medium text-text-primary">Why use OAuth?</h2>
            <ul className="space-y-3 text-sm text-text-secondary">
              <li className="flex items-start gap-2">
                <span className="text-emerald-400 mt-0.5">✓</span>
                <span>No passwords to remember - sign in securely with accounts you trust</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-400 mt-0.5">✓</span>
                <span>Quick and easy registration - just one click to get started</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-400 mt-0.5">✓</span>
                <span>Enhanced security with two-factor authentication from your provider</span>
              </li>
            </ul>
          </div>
        </div>

        {/* CTA */}
        <Link
          to="/login"
          className="btn-primary w-full inline-flex items-center justify-center gap-2"
        >
          Continue to Sign In
          <ArrowRight className="w-5 h-5" />
        </Link>

        <p className="mt-6 text-sm text-text-muted">
          By signing up, you agree to our{' '}
          <a href="#" className="link">
            Terms of Service
          </a>{' '}
          and{' '}
          <a href="#" className="link">
            Privacy Policy
          </a>
        </p>

        {/* Back to home */}
        <p className="mt-8 text-sm text-text-secondary">
          <Link to="/" className="link">
            Back to home
          </Link>
        </p>
      </div>
    </div>
  )
}
