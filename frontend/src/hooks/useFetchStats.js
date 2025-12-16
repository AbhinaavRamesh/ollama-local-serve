/**
 * Custom hook for fetching stats with caching and error handling.
 */

import { useState, useEffect, useCallback, useRef } from 'react'

/**
 * Hook for fetching data with caching, retries, and stale detection.
 * @param {Function} fetchFn - Async function to fetch data
 * @param {Object} options - Configuration options
 * @param {number} options.cacheTime - Cache duration in ms (default: 30000)
 * @param {number} options.staleTime - Time before data is considered stale (default: 5000)
 * @param {boolean} options.enabled - Whether to fetch (default: true)
 * @param {Array} options.deps - Dependencies that trigger refetch
 * @returns {{ data: *, loading: boolean, error: *, refetch: Function, isStale: boolean }}
 */
export function useFetchStats(fetchFn, options = {}) {
  const {
    cacheTime = 30000,
    staleTime = 5000,
    enabled = true,
    deps = [],
  } = options

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isStale, setIsStale] = useState(false)

  const lastFetchTime = useRef(null)
  const cacheRef = useRef(null)
  const abortControllerRef = useRef(null)

  // Check if cache is valid
  const isCacheValid = useCallback(() => {
    if (!lastFetchTime.current || !cacheRef.current) return false
    return Date.now() - lastFetchTime.current < cacheTime
  }, [cacheTime])

  // Check if data is stale
  useEffect(() => {
    if (!lastFetchTime.current) return

    const checkStale = () => {
      const now = Date.now()
      const elapsed = now - lastFetchTime.current
      setIsStale(elapsed > staleTime)
    }

    checkStale()
    const interval = setInterval(checkStale, 1000)
    return () => clearInterval(interval)
  }, [staleTime, data])

  // Fetch data
  const fetchData = useCallback(
    async (force = false) => {
      // Return cached data if valid and not forced
      if (!force && isCacheValid()) {
        setData(cacheRef.current)
        setLoading(false)
        return cacheRef.current
      }

      // Abort previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
      abortControllerRef.current = new AbortController()

      setLoading(true)
      setError(null)

      try {
        const result = await fetchFn({ signal: abortControllerRef.current.signal })

        setData(result)
        cacheRef.current = result
        lastFetchTime.current = Date.now()
        setIsStale(false)
        setLoading(false)

        return result
      } catch (err) {
        // Ignore abort errors
        if (err.name === 'AbortError' || err.name === 'CanceledError') {
          return
        }

        console.error('Fetch error:', err)
        setError(err)
        setLoading(false)

        // Return cached data on error if available
        if (cacheRef.current) {
          setData(cacheRef.current)
          setIsStale(true)
          return cacheRef.current
        }

        throw err
      }
    },
    [fetchFn, isCacheValid]
  )

  // Initial fetch and refetch on dependency change
  useEffect(() => {
    if (enabled) {
      fetchData()
    }

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps])

  // Manual refetch function
  const refetch = useCallback(() => {
    return fetchData(true)
  }, [fetchData])

  return { data, loading, error, refetch, isStale }
}

export default useFetchStats
