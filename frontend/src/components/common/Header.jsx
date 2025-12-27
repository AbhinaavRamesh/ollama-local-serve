/**
 * Application header with navigation and status.
 */

import { Link, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard,
  Activity,
  ScrollText,
  Box,
  Settings,
  Sun,
  Moon,
  Menu,
  X,
  RefreshCw,
  Cpu,
} from 'lucide-react'
import { useState } from 'react'
import { useThemeContext } from '../../context/ThemeContext'
import { useAppContext } from '../../context/AppContext'
import { formatRelativeTime } from '../../utils/formatters'
import { NAV_ITEMS, STATUS_COLORS, HEALTH_STATUS } from '../../utils/constants'
import StatusIndicator from '../dashboard/StatusIndicator'

const iconMap = {
  LayoutDashboard,
  Activity,
  ScrollText,
  Box,
  Settings,
  Cpu,
}

/**
 * Main application header.
 */
export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()
  const { theme, toggleTheme } = useThemeContext()
  const { serviceStatus, lastRefresh, refreshStatus, statusLoading } = useAppContext()

  const statusConfig = HEALTH_STATUS[serviceStatus.status] || HEALTH_STATUS.unhealthy

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 dark:border-slate-700 bg-white/95 dark:bg-slate-900/95 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-slate-900/60">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <Box className="h-5 w-5 text-white" />
              </div>
              <span className="font-bold text-lg text-slate-900 dark:text-white hidden sm:block">
                Ollama Monitor
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const Icon = iconMap[item.icon]
              const isActive = location.pathname === item.path

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={clsx(
                    'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800/50'
                  )}
                >
                  {Icon && <Icon className="h-4 w-4" />}
                  {item.label}
                </Link>
              )
            })}
          </nav>

          {/* Right side actions */}
          <div className="flex items-center gap-3">
            {/* Service Status */}
            <div className="hidden sm:flex items-center gap-3">
              <StatusIndicator
                status={statusConfig.color}
                label={statusConfig.label}
                pulse={serviceStatus.status === 'healthy'}
              />
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {formatRelativeTime(lastRefresh)}
              </span>
            </div>

            {/* Refresh button */}
            <button
              onClick={refreshStatus}
              disabled={statusLoading}
              className="p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
              title="Refresh status"
            >
              <RefreshCw
                className={clsx('h-4 w-4', statusLoading && 'animate-spin')}
              />
            </button>

            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Moon className="h-4 w-4" />
              )}
            </button>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              {mobileMenuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-200 dark:border-slate-700 py-4">
            <nav className="flex flex-col gap-1">
              {NAV_ITEMS.map((item) => {
                const Icon = iconMap[item.icon]
                const isActive = location.pathname === item.path

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={clsx(
                      'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                        : 'text-slate-600 dark:text-slate-400'
                    )}
                  >
                    {Icon && <Icon className="h-5 w-5" />}
                    {item.label}
                  </Link>
                )
              })}
            </nav>

            {/* Mobile status */}
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <div className="flex items-center justify-between px-3">
                <StatusIndicator
                  status={statusConfig.color}
                  label={statusConfig.label}
                  pulse={serviceStatus.status === 'healthy'}
                />
                <span className="text-xs text-slate-500">
                  {formatRelativeTime(lastRefresh)}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}

export default Header
