/**
 * Theme context provider for light/dark mode.
 */

import { createContext, useContext } from 'react'
import { useTheme } from '../hooks/useTheme'

const ThemeContext = createContext(null)

/**
 * Theme provider component.
 */
export function ThemeProvider({ children }) {
  const themeState = useTheme()

  return (
    <ThemeContext.Provider value={themeState}>
      {children}
    </ThemeContext.Provider>
  )
}

/**
 * Hook to access theme context.
 */
export function useThemeContext() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useThemeContext must be used within a ThemeProvider')
  }
  return context
}

export default ThemeContext
