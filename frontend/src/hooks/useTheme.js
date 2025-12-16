/**
 * Custom hook for theme management (light/dark mode).
 */

import { useEffect, useCallback } from 'react'
import { useLocalStorage } from './useLocalStorage'
import { STORAGE_KEYS } from '../utils/constants'

/**
 * Hook for managing theme (light/dark mode).
 * @returns {{ theme: string, toggleTheme: Function, setTheme: Function }}
 */
export function useTheme() {
  // Get initial theme from localStorage or system preference
  const getInitialTheme = () => {
    if (typeof window === 'undefined') return 'light'

    const stored = localStorage.getItem(STORAGE_KEYS.theme)
    if (stored) return stored

    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light'
  }

  const [theme, setThemeState] = useLocalStorage(
    STORAGE_KEYS.theme,
    getInitialTheme()
  )

  // Apply theme to document
  useEffect(() => {
    const root = window.document.documentElement

    root.classList.remove('light', 'dark')
    root.classList.add(theme)

    // Update meta theme-color for mobile browsers
    const metaThemeColor = document.querySelector('meta[name="theme-color"]')
    if (metaThemeColor) {
      metaThemeColor.setAttribute(
        'content',
        theme === 'dark' ? '#0f172a' : '#ffffff'
      )
    }
  }, [theme])

  // Listen for system preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = (e) => {
      // Only update if user hasn't explicitly set a preference
      const stored = localStorage.getItem(STORAGE_KEYS.theme)
      if (!stored) {
        setThemeState(e.matches ? 'dark' : 'light')
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [setThemeState])

  // Toggle between light and dark
  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }, [setThemeState])

  // Set specific theme
  const setTheme = useCallback(
    (newTheme) => {
      if (newTheme === 'light' || newTheme === 'dark') {
        setThemeState(newTheme)
      }
    },
    [setThemeState]
  )

  return { theme, toggleTheme, setTheme }
}

export default useTheme
