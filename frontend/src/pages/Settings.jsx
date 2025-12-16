/**
 * Settings page - configuration and preferences.
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Sun, Moon, Monitor, RefreshCw, Database, Bell, Download } from 'lucide-react'
import { clsx } from 'clsx'
import { useThemeContext } from '../context/ThemeContext'
import { useAppContext } from '../context/AppContext'
import { showSuccess } from '../components/ui/Toast'
import { DEFAULT_REFRESH_INTERVAL } from '../utils/constants'

/**
 * Settings section component.
 */
function SettingsSection({ title, description, children }) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-slate-900 dark:text-white">
          {title}
        </h3>
        {description && (
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {description}
          </p>
        )}
      </div>
      {children}
    </div>
  )
}

/**
 * Settings option component.
 */
function SettingsOption({ icon: Icon, label, description, children }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-200 dark:border-slate-700 last:border-0">
      <div className="flex items-center gap-3">
        {Icon && (
          <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-700">
            <Icon className="h-4 w-4 text-slate-600 dark:text-slate-400" />
          </div>
        )}
        <div>
          <p className="text-sm font-medium text-slate-900 dark:text-white">
            {label}
          </p>
          {description && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {description}
            </p>
          )}
        </div>
      </div>
      <div>{children}</div>
    </div>
  )
}

/**
 * Settings page component.
 */
export function Settings() {
  const { theme, setTheme } = useThemeContext()
  const {
    refreshInterval,
    updateRefreshInterval,
    autoRefreshEnabled,
    toggleAutoRefresh,
  } = useAppContext()

  const [notifications, setNotifications] = useState(true)

  const themeOptions = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
  ]

  const refreshOptions = [
    { value: 1000, label: '1 second' },
    { value: 5000, label: '5 seconds' },
    { value: 10000, label: '10 seconds' },
    { value: 30000, label: '30 seconds' },
    { value: 60000, label: '1 minute' },
  ]

  const handleExportConfig = () => {
    const config = {
      theme,
      refreshInterval,
      autoRefreshEnabled,
      notifications,
      exportedAt: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'ollama-monitor-settings.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    showSuccess('Settings exported successfully')
  }

  const handleResetSettings = () => {
    setTheme('light')
    updateRefreshInterval(DEFAULT_REFRESH_INTERVAL)
    setNotifications(true)
    showSuccess('Settings reset to defaults')
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Settings
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Customize your dashboard experience
        </p>
      </div>

      {/* Appearance */}
      <SettingsSection
        title="Appearance"
        description="Customize how the dashboard looks"
      >
        <SettingsOption
          icon={Sun}
          label="Theme"
          description="Choose your preferred color scheme"
        >
          <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-700 rounded-lg">
            {themeOptions.map((option) => {
              const Icon = option.icon
              return (
                <button
                  key={option.value}
                  onClick={() => setTheme(option.value)}
                  className={clsx(
                    'flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-colors',
                    theme === option.value
                      ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {option.label}
                </button>
              )
            })}
          </div>
        </SettingsOption>
      </SettingsSection>

      {/* Data & Refresh */}
      <SettingsSection
        title="Data & Refresh"
        description="Control how data is fetched and updated"
      >
        <SettingsOption
          icon={RefreshCw}
          label="Auto Refresh"
          description="Automatically refresh data at regular intervals"
        >
          <button
            onClick={toggleAutoRefresh}
            className={clsx(
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
              autoRefreshEnabled
                ? 'bg-blue-600'
                : 'bg-slate-300 dark:bg-slate-600'
            )}
          >
            <span
              className={clsx(
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                autoRefreshEnabled ? 'translate-x-6' : 'translate-x-1'
              )}
            />
          </button>
        </SettingsOption>

        <SettingsOption
          icon={RefreshCw}
          label="Refresh Interval"
          description="How often to fetch new data"
        >
          <select
            value={refreshInterval}
            onChange={(e) => updateRefreshInterval(Number(e.target.value))}
            disabled={!autoRefreshEnabled}
            className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:opacity-50"
          >
            {refreshOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </SettingsOption>
      </SettingsSection>

      {/* Notifications */}
      <SettingsSection
        title="Notifications"
        description="Configure notification preferences"
      >
        <SettingsOption
          icon={Bell}
          label="Enable Notifications"
          description="Show toast notifications for events"
        >
          <button
            onClick={() => setNotifications(!notifications)}
            className={clsx(
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
              notifications
                ? 'bg-blue-600'
                : 'bg-slate-300 dark:bg-slate-600'
            )}
          >
            <span
              className={clsx(
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                notifications ? 'translate-x-6' : 'translate-x-1'
              )}
            />
          </button>
        </SettingsOption>
      </SettingsSection>

      {/* Data Management */}
      <SettingsSection
        title="Data Management"
        description="Export settings and reset preferences"
      >
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleExportConfig}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
          >
            <Download className="h-4 w-4" />
            Export Settings
          </button>
          <button
            onClick={handleResetSettings}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
          >
            Reset to Defaults
          </button>
        </div>
      </SettingsSection>

      {/* About */}
      <SettingsSection title="About">
        <div className="text-sm text-slate-600 dark:text-slate-400 space-y-2">
          <p>
            <span className="font-medium text-slate-900 dark:text-white">
              Ollama Monitor
            </span>{' '}
            v1.0.0
          </p>
          <p>
            A professional monitoring dashboard for Ollama Local Serve.
          </p>
          <p>
            Built with React, TailwindCSS, and Recharts.
          </p>
        </div>
      </SettingsSection>
    </motion.div>
  )
}

export default Settings
