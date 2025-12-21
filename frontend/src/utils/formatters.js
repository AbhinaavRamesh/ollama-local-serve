/**
 * Utility functions for formatting values.
 */

import { format, formatDistanceToNow, parseISO } from 'date-fns'

/**
 * Format a number with optional decimal places and abbreviations (K, M, B).
 * @param {number} num - The number to format
 * @param {number} decimals - Number of decimal places
 * @param {boolean} abbreviate - Whether to abbreviate large numbers
 * @returns {string} Formatted number string
 */
export function formatNumber(num, decimals = 1, abbreviate = true) {
  if (num === null || num === undefined || isNaN(num)) {
    return '0'
  }

  if (!abbreviate) {
    return num.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: decimals,
    })
  }

  const absNum = Math.abs(num)

  if (absNum >= 1_000_000_000) {
    return (num / 1_000_000_000).toFixed(decimals) + 'B'
  }
  if (absNum >= 1_000_000) {
    return (num / 1_000_000).toFixed(decimals) + 'M'
  }
  if (absNum >= 1_000) {
    return (num / 1_000).toFixed(decimals) + 'K'
  }

  // For small decimal values (< 1), show more precision
  if (absNum > 0 && absNum < 1) {
    // Show at least 2 significant digits for small numbers
    if (absNum < 0.01) {
      return num.toFixed(3)
    }
    return num.toFixed(2)
  }

  return num.toFixed(decimals)
}

/**
 * Format duration in milliseconds to human-readable string.
 * @param {number} ms - Duration in milliseconds
 * @returns {string} Formatted duration
 */
export function formatDuration(ms) {
  if (ms === null || ms === undefined || isNaN(ms)) {
    return '0ms'
  }

  if (ms < 1) {
    return `${(ms * 1000).toFixed(0)}µs`
  }
  if (ms < 1000) {
    return `${ms.toFixed(0)}ms`
  }
  if (ms < 60000) {
    return `${(ms / 1000).toFixed(1)}s`
  }
  if (ms < 3600000) {
    const mins = Math.floor(ms / 60000)
    const secs = Math.floor((ms % 60000) / 1000)
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`
  }

  const hours = Math.floor(ms / 3600000)
  const mins = Math.floor((ms % 3600000) / 60000)
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
}

/**
 * Format a timestamp to a human-readable string.
 * @param {string|Date} date - The date to format
 * @param {string} formatStr - The format string (date-fns)
 * @returns {string} Formatted timestamp
 */
export function formatTimestamp(date, formatStr = 'MMM d, yyyy HH:mm:ss') {
  if (!date) return '-'

  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date
    return format(dateObj, formatStr)
  } catch {
    return '-'
  }
}

/**
 * Format a timestamp to relative time (e.g., "2 minutes ago").
 * @param {string|Date} date - The date to format
 * @returns {string} Relative time string
 */
export function formatRelativeTime(date) {
  if (!date) return '-'

  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date
    return formatDistanceToNow(dateObj, { addSuffix: true })
  } catch {
    return '-'
  }
}

/**
 * Format bytes to human-readable string.
 * @param {number} bytes - The number of bytes
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted bytes string
 */
export function formatBytes(bytes, decimals = 1) {
  if (bytes === 0) return '0 B'
  if (!bytes || isNaN(bytes)) return '0 B'

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`
}

/**
 * Format tokens count with appropriate suffix.
 * @param {number} count - Number of tokens
 * @returns {string} Formatted token count
 */
export function formatTokens(count) {
  if (!count || isNaN(count)) return '0 tokens'

  const formatted = formatNumber(count)
  return `${formatted} tokens`
}

/**
 * Format latency with color indication.
 * @param {number} ms - Latency in milliseconds
 * @returns {{ value: string, color: string }} Formatted latency with color
 */
export function formatLatency(ms) {
  const formatted = formatDuration(ms)

  let color = 'text-emerald-600 dark:text-emerald-400'
  if (ms > 1000) {
    color = 'text-red-600 dark:text-red-400'
  } else if (ms > 500) {
    color = 'text-amber-600 dark:text-amber-400'
  }

  return { value: formatted, color }
}

/**
 * Calculate trend between two values.
 * @param {number} current - Current value
 * @param {number} previous - Previous value
 * @returns {{ value: number, percentage: number, positive: boolean }} Trend info
 */
export function calculateTrend(current, previous) {
  if (!previous || previous === 0) {
    return { value: current, percentage: 0, positive: true }
  }

  const diff = current - previous
  const percentage = ((diff / previous) * 100)
  const positive = diff >= 0

  return {
    value: Math.abs(diff),
    percentage: Math.abs(percentage),
    positive,
  }
}

/**
 * Format percentage value.
 * @param {number} value - The value (0-100 or 0-1)
 * @param {boolean} isDecimal - Whether value is 0-1 scale
 * @returns {string} Formatted percentage
 */
export function formatPercentage(value, isDecimal = false) {
  if (value === null || value === undefined || isNaN(value)) {
    return '0%'
  }

  const pct = isDecimal ? value * 100 : value
  return `${pct.toFixed(1)}%`
}

/**
 * Format uptime in seconds to human-readable string.
 * @param {number} seconds - Uptime in seconds
 * @returns {string} Formatted uptime
 */
export function formatUptime(seconds) {
  if (!seconds || isNaN(seconds)) return '0s'

  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  const parts = []
  if (days > 0) parts.push(`${days}d`)
  if (hours > 0) parts.push(`${hours}h`)
  if (minutes > 0 && days === 0) parts.push(`${minutes}m`)
  if (parts.length === 0) parts.push(`${Math.floor(seconds)}s`)

  return parts.join(' ')
}

/**
 * Truncate text with ellipsis.
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
export function truncate(text, maxLength = 50) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
}
