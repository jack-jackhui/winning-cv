import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'

// Layouts
import PublicLayout from './components/layout/PublicLayout'
import DashboardLayout from './components/layout/DashboardLayout'

// Public pages
import Landing from './pages/Landing'
import Login from './pages/Login'
import Signup from './pages/Signup'
import AuthCallback from './pages/AuthCallback'
import GitHubCallback from './pages/GitHubCallback'

// Protected pages
import Dashboard from './pages/Dashboard'
import UploadCV from './pages/UploadCV'
import Preferences from './pages/Preferences'
import GenerateCV from './pages/GenerateCV'
import History from './pages/History'
import Profile from './pages/Profile'
import CVLibrary from './pages/CVLibrary'
import CVAnalytics from './pages/CVAnalytics'

// Protected route wrapper
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}

// Public route wrapper (redirect to dashboard if logged in)
function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Landing />} />
        <Route
          path="/login"
          element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          }
        />
        <Route
          path="/signup"
          element={
            <PublicRoute>
              <Signup />
            </PublicRoute>
          }
        />
        {/* OAuth callback routes */}
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/auth/github/callback" element={<GitHubCallback />} />
      </Route>

      {/* Protected routes */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/upload" element={<UploadCV />} />
        <Route path="/preferences" element={<Preferences />} />
        <Route path="/generate" element={<GenerateCV />} />
        <Route path="/history" element={<History />} />
        <Route path="/cv-library" element={<CVLibrary />} />
        <Route path="/cv-analytics" element={<CVAnalytics />} />
        <Route path="/profile" element={<Profile />} />
      </Route>

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
