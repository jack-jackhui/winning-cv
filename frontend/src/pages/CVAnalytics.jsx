/**
 * CVAnalytics - Dashboard for CV version performance metrics
 *
 * Shows usage statistics, response rates, and performance trends
 * for all CV versions in the user's library.
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  FileText,
  Send,
  MessageSquare,
  Percent,
  Calendar,
  ArrowRight,
  Loader2,
  AlertCircle,
  FolderOpen,
  Star,
  Activity,
} from 'lucide-react'
import { cvVersionsService } from '../services/api'

// Stat card component
function StatCard({ title, value, subtitle, icon: Icon, trend, trendValue, color = 'accent' }) {
  const colorClasses = {
    accent: 'bg-accent-500/20 text-accent-400',
    emerald: 'bg-emerald-500/20 text-emerald-400',
    amber: 'bg-amber-500/20 text-amber-400',
    purple: 'bg-purple-500/20 text-purple-400',
  }

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div className={`p-3 rounded-xl ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        {trend && (
          <div
            className={`flex items-center gap-1 text-sm ${
              trend === 'up' ? 'text-emerald-400' : 'text-red-400'
            }`}
          >
            {trend === 'up' ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            {trendValue}
          </div>
        )}
      </div>
      <div className="mt-4">
        <h3 className="text-3xl font-bold text-text-primary">{value}</h3>
        <p className="text-sm text-text-muted mt-1">{title}</p>
        {subtitle && <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}

// Top performer card
function TopPerformerCard({ version, rank }) {
  const responseRate = version.usage_count > 0
    ? ((version.response_count / version.usage_count) * 100).toFixed(0)
    : 0

  return (
    <div className="flex items-center gap-4 p-4 rounded-xl bg-surface-elevated border border-border">
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
          rank === 1
            ? 'bg-amber-500/20 text-amber-400'
            : rank === 2
              ? 'bg-slate-400/20 text-slate-400'
              : 'bg-amber-700/20 text-amber-600'
        }`}
      >
        {rank}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-text-primary truncate">{version.version_name}</p>
        <p className="text-sm text-text-muted">
          {version.auto_category || 'General'}
        </p>
      </div>
      <div className="text-right">
        <p className="font-semibold text-emerald-400">{responseRate}%</p>
        <p className="text-xs text-text-muted">response rate</p>
      </div>
    </div>
  )
}

// Category breakdown card
function CategoryCard({ category, count, totalUsage, totalResponses }) {
  const responseRate = totalUsage > 0 ? ((totalResponses / totalUsage) * 100).toFixed(0) : 0

  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-surface hover:bg-surface-elevated transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-accent-500" />
        <span className="text-text-primary">{category || 'Uncategorized'}</span>
      </div>
      <div className="flex items-center gap-4 text-sm">
        <span className="text-text-muted">{count} CVs</span>
        <span className="text-text-muted">{totalUsage} uses</span>
        <span className="text-emerald-400">{responseRate}%</span>
      </div>
    </div>
  )
}

export default function CVAnalytics() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [versions, setVersions] = useState([])

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [analyticsData, versionsData] = await Promise.all([
        cvVersionsService.getAnalytics(),
        cvVersionsService.listVersions({ limit: 100 }),
      ])
      setAnalytics(analyticsData)
      setVersions(versionsData.items || [])
    } catch (err) {
      console.error('Failed to load analytics:', err)
      setError(err.message || 'Failed to load analytics data')
    } finally {
      setLoading(false)
    }
  }

  // Calculate derived metrics
  const getTopPerformers = () => {
    return [...versions]
      .filter((v) => v.usage_count > 0)
      .sort((a, b) => {
        const rateA = a.response_count / a.usage_count
        const rateB = b.response_count / b.usage_count
        return rateB - rateA
      })
      .slice(0, 5)
  }

  const getCategoryBreakdown = () => {
    const categories = {}
    versions.forEach((v) => {
      const cat = v.auto_category || 'Uncategorized'
      if (!categories[cat]) {
        categories[cat] = { count: 0, usage: 0, responses: 0 }
      }
      categories[cat].count++
      categories[cat].usage += v.usage_count || 0
      categories[cat].responses += v.response_count || 0
    })
    return Object.entries(categories)
      .map(([name, data]) => ({ name, ...data }))
      .sort((a, b) => b.usage - a.usage)
  }

  const getRecentActivity = () => {
    return [...versions]
      .filter((v) => v.last_used_at)
      .sort((a, b) => new Date(b.last_used_at) - new Date(a.last_used_at))
      .slice(0, 5)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-accent-500 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
        <h2 className="text-lg font-medium text-text-primary mb-2">Failed to load analytics</h2>
        <p className="text-text-muted mb-4">{error}</p>
        <button onClick={loadData} className="btn-primary">
          Try Again
        </button>
      </div>
    )
  }

  const topPerformers = getTopPerformers()
  const categoryBreakdown = getCategoryBreakdown()
  const recentActivity = getRecentActivity()

  const overallResponseRate =
    analytics?.total_usage > 0
      ? ((analytics.total_responses / analytics.total_usage) * 100).toFixed(1)
      : 0

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
            <BarChart3 className="w-7 h-7 text-accent-400" />
            CV Analytics
          </h1>
          <p className="mt-1 text-text-secondary">
            Track your CV performance and optimize for better results
          </p>
        </div>
        <Link to="/cv-library" className="btn-secondary">
          <FolderOpen className="w-4 h-4 mr-2" />
          View Library
        </Link>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total CVs"
          value={analytics?.total_versions || versions.length}
          subtitle={`${analytics?.active_versions || versions.filter((v) => !v.is_archived).length} active`}
          icon={FileText}
          color="accent"
        />
        <StatCard
          title="Applications Sent"
          value={analytics?.total_usage || 0}
          subtitle="Total CV uses"
          icon={Send}
          color="purple"
        />
        <StatCard
          title="Responses Received"
          value={analytics?.total_responses || 0}
          subtitle="Callbacks & interviews"
          icon={MessageSquare}
          color="emerald"
        />
        <StatCard
          title="Response Rate"
          value={`${overallResponseRate}%`}
          subtitle="Overall success rate"
          icon={Percent}
          color="amber"
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Top Performers */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-text-primary flex items-center gap-2">
              <Star className="w-5 h-5 text-amber-400" />
              Top Performers
            </h2>
            <span className="text-sm text-text-muted">By response rate</span>
          </div>

          {topPerformers.length > 0 ? (
            <div className="space-y-3">
              {topPerformers.map((version, index) => (
                <TopPerformerCard
                  key={version.version_id}
                  version={version}
                  rank={index + 1}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Activity className="w-10 h-10 text-text-muted mx-auto mb-2" />
              <p className="text-text-secondary">No usage data yet</p>
              <p className="text-sm text-text-muted">
                Start using your CVs to see performance metrics
              </p>
            </div>
          )}
        </div>

        {/* Category Breakdown */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-text-primary flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-accent-400" />
              By Category
            </h2>
            <span className="text-sm text-text-muted">Usage distribution</span>
          </div>

          {categoryBreakdown.length > 0 ? (
            <div className="space-y-2">
              {categoryBreakdown.map((cat) => (
                <CategoryCard
                  key={cat.name}
                  category={cat.name}
                  count={cat.count}
                  totalUsage={cat.usage}
                  totalResponses={cat.responses}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <FolderOpen className="w-10 h-10 text-text-muted mx-auto mb-2" />
              <p className="text-text-secondary">No categories yet</p>
              <p className="text-sm text-text-muted">
                CVs are auto-categorized when uploaded
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-text-primary flex items-center gap-2">
            <Calendar className="w-5 h-5 text-accent-400" />
            Recent Activity
          </h2>
          <Link
            to="/cv-library"
            className="text-sm text-accent-400 hover:text-accent-300 flex items-center gap-1"
          >
            View all
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {recentActivity.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-sm font-medium text-text-muted">
                    CV Version
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-text-muted">
                    Category
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-text-muted">
                    Uses
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-text-muted">
                    Responses
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-text-muted">
                    Last Used
                  </th>
                </tr>
              </thead>
              <tbody>
                {recentActivity.map((version) => (
                  <tr
                    key={version.version_id}
                    className="border-b border-border/50 hover:bg-surface-elevated transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-accent-400" />
                        <span className="font-medium text-text-primary">
                          {version.version_name}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-text-muted">
                      {version.auto_category || '-'}
                    </td>
                    <td className="py-3 px-4 text-center text-text-primary">
                      {version.usage_count}
                    </td>
                    <td className="py-3 px-4 text-center text-emerald-400">
                      {version.response_count}
                    </td>
                    <td className="py-3 px-4 text-right text-text-muted text-sm">
                      {version.last_used_at
                        ? new Date(version.last_used_at).toLocaleDateString()
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8">
            <Calendar className="w-10 h-10 text-text-muted mx-auto mb-2" />
            <p className="text-text-secondary">No recent activity</p>
            <p className="text-sm text-text-muted">
              Start applying with your CVs to track activity
            </p>
          </div>
        )}
      </div>

      {/* Tips Section */}
      <div className="card bg-gradient-to-r from-accent-500/10 to-purple-500/10 border-accent-500/20">
        <h2 className="font-semibold text-text-primary mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-accent-400" />
          Tips to Improve Your Response Rate
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-surface/50">
            <h3 className="font-medium text-text-primary mb-1">Tailor for each role</h3>
            <p className="text-sm text-text-muted">
              Use the smart matching feature to select the best CV for each job application.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-surface/50">
            <h3 className="font-medium text-text-primary mb-1">Track your responses</h3>
            <p className="text-sm text-text-muted">
              Mark responses when you get callbacks to improve the matching algorithm.
            </p>
          </div>
          <div className="p-4 rounded-lg bg-surface/50">
            <h3 className="font-medium text-text-primary mb-1">Create specialized versions</h3>
            <p className="text-sm text-text-muted">
              Fork high-performing CVs and customize them for specific industries.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
