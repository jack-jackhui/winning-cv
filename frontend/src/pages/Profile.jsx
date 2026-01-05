import { useState, useEffect } from 'react'
import {
  User,
  Mail,
  Bell,
  Shield,
  Save,
  Loader2,
  CheckCircle2,
  Trash2,
  LogOut,
  Send,
  AlertCircle,
  MessageCircle,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { profileService } from '../services/api'

export default function Profile() {
  const { user, logout } = useAuth()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loadingPrefs, setLoadingPrefs] = useState(true)
  const [error, setError] = useState(null)
  const [testingChannel, setTestingChannel] = useState(null)
  const [testResult, setTestResult] = useState(null)

  const [profile, setProfile] = useState({
    name: user?.display_name || user?.name || '',
    email: user?.email || '',
  })

  const [notifications, setNotifications] = useState({
    emailAlerts: true,
    telegramAlerts: false,
    wechatAlerts: false,
    weeklyDigest: true,
    telegramChatId: '',
    wechatOpenId: '',
    notificationEmail: '',
  })

  // Load notification preferences on mount
  useEffect(() => {
    async function loadPreferences() {
      try {
        setLoadingPrefs(true)
        const prefs = await profileService.getNotificationPreferences()
        setNotifications({
          emailAlerts: prefs.email_alerts ?? true,
          telegramAlerts: prefs.telegram_alerts ?? false,
          wechatAlerts: prefs.wechat_alerts ?? false,
          weeklyDigest: prefs.weekly_digest ?? true,
          telegramChatId: prefs.telegram_chat_id || '',
          wechatOpenId: prefs.wechat_openid || '',
          notificationEmail: prefs.notification_email || user?.email || '',
        })
      } catch (err) {
        console.error('Failed to load notification preferences:', err)
        // Use defaults on error
      } finally {
        setLoadingPrefs(false)
      }
    }

    if (user) {
      loadPreferences()
    }
  }, [user])

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setSaving(true)
    setSaved(false)
    setError(null)

    try {
      await profileService.updateProfile(profile)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      console.error('Failed to save profile:', err)
      setError('Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveNotifications = async () => {
    setSaving(true)
    setSaved(false)
    setError(null)

    // Validate: if telegram alerts enabled, chat ID is required
    if (notifications.telegramAlerts && !notifications.telegramChatId) {
      setError('Telegram Chat ID is required when enabling Telegram alerts')
      setSaving(false)
      return
    }

    try {
      await profileService.updateNotificationPreferences(notifications)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      console.error('Failed to save notifications:', err)
      setError(err.message || 'Failed to save notification preferences')
    } finally {
      setSaving(false)
    }
  }

  const handleTestNotification = async (channel) => {
    setTestingChannel(channel)
    setTestResult(null)

    try {
      const result = await profileService.testNotification(channel)
      setTestResult({
        success: result.success,
        channel: result.channel,
        message: result.message,
      })
    } catch (err) {
      setTestResult({
        success: false,
        channel,
        message: err.message || 'Failed to send test notification',
      })
    } finally {
      setTestingChannel(null)
      // Clear result after 5 seconds
      setTimeout(() => setTestResult(null), 5000)
    }
  }

  const handleDeleteAccount = async () => {
    if (
      !confirm(
        'Are you sure you want to delete your account? This action cannot be undone.'
      )
    ) {
      return
    }

    try {
      await profileService.deleteAccount()
      logout()
    } catch (err) {
      console.error('Failed to delete account:', err)
      setError('Failed to delete account')
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Profile Settings</h1>
        <p className="mt-1 text-text-secondary">
          Manage your account and notification preferences
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Profile Info */}
      <form onSubmit={handleSaveProfile} className="card space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-accent-500/10 flex items-center justify-center">
            <User className="w-5 h-5 text-accent-400" />
          </div>
          <div>
            <h2 className="font-medium text-text-primary">Personal Information</h2>
            <p className="text-sm text-text-muted">Update your account details</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label htmlFor="name" className="input-label">
              Full name
            </label>
            <input
              id="name"
              type="text"
              value={profile.name}
              onChange={(e) => setProfile({ ...profile, name: e.target.value })}
              className="input"
            />
          </div>

          <div>
            <label htmlFor="email" className="input-label">
              Email address
            </label>
            <input
              id="email"
              type="email"
              value={profile.email}
              disabled
              className="input opacity-60 cursor-not-allowed"
            />
            <p className="text-xs text-text-muted mt-1">
              Email is managed by your OAuth provider
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Save className="w-5 h-5" />
                Save Changes
              </>
            )}
          </button>
          {saved && (
            <span className="flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              Saved
            </span>
          )}
        </div>
      </form>

      {/* Notifications */}
      <div className="card space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-accent-500/10 flex items-center justify-center">
            <Bell className="w-5 h-5 text-accent-400" />
          </div>
          <div>
            <h2 className="font-medium text-text-primary">Notifications</h2>
            <p className="text-sm text-text-muted">
              Choose how you want to be notified about job matches
            </p>
          </div>
        </div>

        {loadingPrefs ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-accent-400" />
          </div>
        ) : (
          <div className="space-y-4">
            {/* Email Alerts */}
            <div className="p-4 rounded-xl bg-surface-elevated space-y-3">
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <Mail className="w-5 h-5 text-text-muted" />
                  <div>
                    <p className="font-medium text-text-primary">Email Alerts</p>
                    <p className="text-sm text-text-muted">
                      Get notified about new job matches via email
                    </p>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={notifications.emailAlerts}
                  onChange={(e) =>
                    setNotifications({
                      ...notifications,
                      emailAlerts: e.target.checked,
                    })
                  }
                  className="w-5 h-5 rounded border-border bg-surface text-accent-600 focus:ring-accent-500"
                />
              </label>
              {notifications.emailAlerts && (
                <div className="pl-8 space-y-2">
                  <input
                    type="email"
                    placeholder="Notification email (optional)"
                    value={notifications.notificationEmail}
                    onChange={(e) =>
                      setNotifications({
                        ...notifications,
                        notificationEmail: e.target.value,
                      })
                    }
                    className="input text-sm"
                  />
                  <p className="text-xs text-text-muted">
                    Leave empty to use your account email
                  </p>
                  <button
                    type="button"
                    onClick={() => handleTestNotification('email')}
                    disabled={testingChannel === 'email'}
                    className="btn-secondary text-sm py-1.5 px-3"
                  >
                    {testingChannel === 'email' ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        Send Test
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Telegram Alerts */}
            <div className="p-4 rounded-xl bg-surface-elevated space-y-3">
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <MessageCircle className="w-5 h-5 text-text-muted" />
                  <div>
                    <p className="font-medium text-text-primary">Telegram Alerts</p>
                    <p className="text-sm text-text-muted">
                      Receive instant notifications on Telegram
                    </p>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={notifications.telegramAlerts}
                  onChange={(e) =>
                    setNotifications({
                      ...notifications,
                      telegramAlerts: e.target.checked,
                    })
                  }
                  className="w-5 h-5 rounded border-border bg-surface text-accent-600 focus:ring-accent-500"
                />
              </label>
              {notifications.telegramAlerts && (
                <div className="pl-8 space-y-2">
                  <input
                    type="text"
                    placeholder="Your Telegram Chat ID"
                    value={notifications.telegramChatId}
                    onChange={(e) =>
                      setNotifications({
                        ...notifications,
                        telegramChatId: e.target.value,
                      })
                    }
                    className="input text-sm"
                    required
                  />
                  <p className="text-xs text-text-muted">
                    Send /start to @userinfobot on Telegram to get your Chat ID
                  </p>
                  <button
                    type="button"
                    onClick={() => handleTestNotification('telegram')}
                    disabled={testingChannel === 'telegram' || !notifications.telegramChatId}
                    className="btn-secondary text-sm py-1.5 px-3"
                  >
                    {testingChannel === 'telegram' ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        Send Test
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* WeChat Alerts */}
            <div className="p-4 rounded-xl bg-surface-elevated space-y-3">
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <Bell className="w-5 h-5 text-text-muted" />
                  <div>
                    <p className="font-medium text-text-primary">WeChat Alerts</p>
                    <p className="text-sm text-text-muted">
                      Get notifications through WeChat Work
                    </p>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={notifications.wechatAlerts}
                  onChange={(e) =>
                    setNotifications({
                      ...notifications,
                      wechatAlerts: e.target.checked,
                    })
                  }
                  className="w-5 h-5 rounded border-border bg-surface text-accent-600 focus:ring-accent-500"
                />
              </label>
              {notifications.wechatAlerts && (
                <div className="pl-8 space-y-2">
                  <p className="text-xs text-text-muted">
                    WeChat notifications are sent via the configured WeChat Work webhook
                  </p>
                  <button
                    type="button"
                    onClick={() => handleTestNotification('wechat')}
                    disabled={testingChannel === 'wechat'}
                    className="btn-secondary text-sm py-1.5 px-3"
                  >
                    {testingChannel === 'wechat' ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        Send Test
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Weekly Digest */}
            <label className="flex items-center justify-between p-4 rounded-xl bg-surface-elevated cursor-pointer">
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-text-muted" />
                <div>
                  <p className="font-medium text-text-primary">Weekly Digest</p>
                  <p className="text-sm text-text-muted">
                    Receive a weekly summary of your job search
                  </p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={notifications.weeklyDigest}
                onChange={(e) =>
                  setNotifications({
                    ...notifications,
                    weeklyDigest: e.target.checked,
                  })
                }
                className="w-5 h-5 rounded border-border bg-surface text-accent-600 focus:ring-accent-500"
              />
            </label>

            {/* Test Result */}
            {testResult && (
              <div
                className={`flex items-center gap-3 p-4 rounded-xl ${
                  testResult.success
                    ? 'bg-emerald-500/10 border border-emerald-500/20'
                    : 'bg-red-500/10 border border-red-500/20'
                }`}
              >
                {testResult.success ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                )}
                <p className={testResult.success ? 'text-emerald-400' : 'text-red-400'}>
                  {testResult.message}
                </p>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center gap-4">
          <button
            onClick={handleSaveNotifications}
            disabled={saving || loadingPrefs}
            className="btn-primary"
          >
            {saving ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Save className="w-5 h-5" />
                Save Preferences
              </>
            )}
          </button>
          {saved && (
            <span className="flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              Saved
            </span>
          )}
        </div>
      </div>

      {/* Account Actions */}
      <div className="card space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-accent-500/10 flex items-center justify-center">
            <Shield className="w-5 h-5 text-accent-400" />
          </div>
          <div>
            <h2 className="font-medium text-text-primary">Account</h2>
            <p className="text-sm text-text-muted">Manage your account</p>
          </div>
        </div>

        <div className="space-y-3">
          <button
            onClick={logout}
            className="btn-secondary w-full justify-start text-text-secondary"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>

          <button
            onClick={handleDeleteAccount}
            className="btn w-full justify-start bg-red-500/10 text-red-400 hover:bg-red-500/20 px-6 py-3"
          >
            <Trash2 className="w-5 h-5" />
            Delete Account
          </button>
        </div>
      </div>
    </div>
  )
}
