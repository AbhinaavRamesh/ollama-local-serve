/**
 * Custom hook for auto-refreshing data at intervals.
 */

import { useEffect, useRef, useCallback, useState } from 'react'

/**
 * Hook for auto-refreshing data.
 * @param {Function} callback - Function to call on each refresh
 * @param {number} interval - Refresh interval in milliseconds
 * @param {boolean} enabled - Whether auto-refresh is enabled
 * @returns {{ lastRefresh: Date, pause: Function, resume: Function, refresh: Function, isPaused: boolean }}
 */
export function useAutoRefresh(callback, interval = 5000, enabled = true) {
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const [isPaused, setIsPaused] = useState(!enabled)
  const savedCallback = useRef(callback)
  const intervalRef = useRef(null)

  // Remember the latest callback
  useEffect(() => {
    savedCallback.current = callback
  }, [callback])

  // Clear interval on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [])

  // Start/stop interval based on enabled state
  useEffect(() => {
    if (enabled && !isPaused) {
      // Initial call
      savedCallback.current()
      setLastRefresh(new Date())

      // Set up interval
      intervalRef.current = setInterval(() => {
        savedCallback.current()
        setLastRefresh(new Date())
      }, interval)
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [enabled, isPaused, interval])

  // Pause/resume when tab visibility changes
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Pause when tab is hidden
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
      } else {
        // Resume when tab is visible (if not manually paused)
        if (enabled && !isPaused) {
          savedCallback.current()
          setLastRefresh(new Date())
          intervalRef.current = setInterval(() => {
            savedCallback.current()
            setLastRefresh(new Date())
          }, interval)
        }
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [enabled, isPaused, interval])

  // Pause refreshing
  const pause = useCallback(() => {
    setIsPaused(true)
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  // Resume refreshing
  const resume = useCallback(() => {
    setIsPaused(false)
  }, [])

  // Manual refresh
  const refresh = useCallback(() => {
    savedCallback.current()
    setLastRefresh(new Date())
  }, [])

  return { lastRefresh, pause, resume, refresh, isPaused }
}

export default useAutoRefresh
