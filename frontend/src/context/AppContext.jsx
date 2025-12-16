/**
 * Global application context for shared state.
 */

import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { fetchHealth } from '../utils/api'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { useLocalStorage } from '../hooks/useLocalStorage'
import { STORAGE_KEYS, DEFAULT_REFRESH_INTERVAL } from '../utils/constants'

const AppContext = createContext(null)

/**
 * App state provider component.
 */
export function AppProvider({ children }) {
  // Service status
  const [serviceStatus, setServiceStatus] = useState({
    status: 'unknown',
    uptime: 0,
    databaseConnected: false,
  })
  const [statusLoading, setStatusLoading] = useState(true)
  const [statusError, setStatusError] = useState(null)

  // Settings
  const [refreshInterval, setRefreshInterval] = useLocalStorage(
    STORAGE_KEYS.refreshInterval,
    DEFAULT_REFRESH_INTERVAL
  )
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true)

  // Fetch service status
  const fetchServiceStatus = useCallback(async () => {
    try {
      setStatusLoading(true)
      const health = await fetchHealth()
      setServiceStatus({
        status: health.status,
        uptime: health.uptime_seconds,
        databaseConnected: health.database_connected,
        details: health.details,
      })
      setStatusError(null)
    } catch (err) {
      setStatusError(err.message)
      setServiceStatus((prev) => ({
        ...prev,
        status: 'unhealthy',
      }))
    } finally {
      setStatusLoading(false)
    }
  }, [])

  // Auto-refresh status
  const { lastRefresh, refresh: refreshStatus } = useAutoRefresh(
    fetchServiceStatus,
    refreshInterval,
    autoRefreshEnabled
  )

  // Initial fetch
  useEffect(() => {
    fetchServiceStatus()
  }, [fetchServiceStatus])

  // Toggle auto-refresh
  const toggleAutoRefresh = useCallback(() => {
    setAutoRefreshEnabled((prev) => !prev)
  }, [])

  // Update refresh interval
  const updateRefreshInterval = useCallback(
    (interval) => {
      setRefreshInterval(interval)
    },
    [setRefreshInterval]
  )

  const value = {
    // Service status
    serviceStatus,
    statusLoading,
    statusError,
    refreshStatus,
    lastRefresh,

    // Settings
    refreshInterval,
    autoRefreshEnabled,
    toggleAutoRefresh,
    updateRefreshInterval,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

/**
 * Hook to access app context.
 */
export function useAppContext() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider')
  }
  return context
}

export default AppContext
