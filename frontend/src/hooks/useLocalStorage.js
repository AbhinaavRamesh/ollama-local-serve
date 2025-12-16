/**
 * Custom hook for persisting state to localStorage.
 */

import { useState, useEffect, useCallback } from 'react'

/**
 * Hook to persist state in localStorage.
 * @param {string} key - Storage key
 * @param {*} initialValue - Initial value if not in storage
 * @returns {[*, Function]} State value and setter
 */
export function useLocalStorage(key, initialValue) {
  // Initialize state from localStorage or use initial value
  const [storedValue, setStoredValue] = useState(() => {
    if (typeof window === 'undefined') {
      return initialValue
    }

    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error)
      return initialValue
    }
  })

  // Update localStorage when state changes
  const setValue = useCallback(
    (value) => {
      try {
        // Allow value to be a function (like useState)
        const valueToStore =
          value instanceof Function ? value(storedValue) : value

        setStoredValue(valueToStore)

        if (typeof window !== 'undefined') {
          window.localStorage.setItem(key, JSON.stringify(valueToStore))

          // Dispatch custom event for cross-tab sync
          window.dispatchEvent(
            new StorageEvent('storage', {
              key,
              newValue: JSON.stringify(valueToStore),
            })
          )
        }
      } catch (error) {
        console.warn(`Error setting localStorage key "${key}":`, error)
      }
    },
    [key, storedValue]
  )

  // Listen for changes from other tabs
  useEffect(() => {
    const handleStorageChange = (event) => {
      if (event.key === key && event.newValue !== null) {
        try {
          setStoredValue(JSON.parse(event.newValue))
        } catch (error) {
          console.warn(`Error parsing storage event for "${key}":`, error)
        }
      }
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [key])

  return [storedValue, setValue]
}

export default useLocalStorage
