import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Search,
  FileText,
  History,
  User,
  LogOut,
  ChevronLeft,
  ChevronRight,
  FolderOpen,
  BarChart3,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'My CVs', href: '/cv-library', icon: FolderOpen },
  { name: 'CV Analytics', href: '/cv-analytics', icon: BarChart3 },
  { name: 'Generate CV', href: '/generate', icon: FileText },
  { name: 'Job Search', href: '/preferences', icon: Search },
  { name: 'CV History', href: '/history', icon: History },
  { name: 'Profile', href: '/profile', icon: User },
]

export default function Sidebar({ collapsed, onToggle }) {
  const location = useLocation()
  const { user, logout } = useAuth()

  return (
    <aside
      className={`fixed top-0 left-0 h-full bg-surface border-r border-border z-40 transition-all duration-300 ${
        collapsed ? 'w-20' : 'w-64'
      }`}
    >
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="h-16 lg:h-20 flex items-center justify-between px-4 border-b border-border">
          <Link to="/dashboard" className="flex items-center gap-2 overflow-hidden">
            <div className="w-10 h-10 bg-accent-600 rounded-xl flex items-center justify-center flex-shrink-0">
              <FileText className="w-5 h-5 text-white" />
            </div>
            {!collapsed && (
              <span className="text-lg font-semibold text-text-primary whitespace-nowrap">
                WinningCV
              </span>
            )}
          </Link>
          <button
            onClick={onToggle}
            className="btn-icon hidden lg:flex"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={isActive ? 'nav-item-active' : 'nav-item'}
                title={collapsed ? item.name : undefined}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {!collapsed && <span>{item.name}</span>}
              </Link>
            )
          })}
        </nav>

        {/* User section */}
        <div className="p-3 border-t border-border">
          {!collapsed && user && (
            <div className="px-4 py-3 mb-2">
              <p className="text-sm font-medium text-text-primary truncate">{user.name}</p>
              <p className="text-xs text-text-muted truncate">{user.email}</p>
            </div>
          )}
          <button
            onClick={logout}
            className="nav-item w-full text-red-400 hover:text-red-300 hover:bg-red-500/10"
            title={collapsed ? 'Sign out' : undefined}
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span>Sign out</span>}
          </button>
        </div>
      </div>
    </aside>
  )
}
