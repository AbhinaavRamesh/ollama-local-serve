/**
 * API client for the Ollama monitoring backend.
 */

import axios from 'axios'
import { API_ENDPOINTS } from './constants'

// Create axios instance with default config
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging and auth
api.interceptors.request.use(
  (config) => {
    // Add timestamp to prevent caching
    config.params = {
      ...config.params,
      _t: Date.now(),
    }
    return config
  },
  (error) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Retry logic for network errors
    if (!error.response && !originalRequest._retry) {
      originalRequest._retry = true
      originalRequest._retryCount = (originalRequest._retryCount || 0) + 1

      if (originalRequest._retryCount <= 3) {
        // Exponential backoff
        const delay = Math.pow(2, originalRequest._retryCount) * 1000
        await new Promise((resolve) => setTimeout(resolve, delay))
        return api(originalRequest)
      }
    }

    // Format error message
    const message =
      error.response?.data?.message ||
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred'

    console.error('API Error:', {
      status: error.response?.status,
      message,
      url: originalRequest?.url,
    })

    return Promise.reject({
      status: error.response?.status,
      message,
      data: error.response?.data,
    })
  }
)

/**
 * Fetch current stats.
 * @returns {Promise<Object>} Current stats data
 */
export async function fetchCurrentStats() {
  const response = await api.get(API_ENDPOINTS.stats.current)
  return response.data
}

/**
 * Fetch stats history.
 * @param {string} timeRange - Time range (1h, 6h, 24h)
 * @param {string} granularity - Data granularity (1m, 5m, 1h)
 * @returns {Promise<Object>} History data
 */
export async function fetchStatsHistory(timeRange = '1h', granularity = '1m') {
  const response = await api.get(API_ENDPOINTS.stats.history, {
    params: { time_range: timeRange, granularity },
  })
  return response.data
}

/**
 * Fetch request logs.
 * @param {Object} params - Query parameters
 * @param {number} params.limit - Number of logs to fetch
 * @param {number} params.offset - Offset for pagination
 * @param {string} params.status - Filter by status
 * @param {string} params.model - Filter by model
 * @returns {Promise<Object>} Logs data with pagination
 */
export async function fetchLogs({ limit = 25, offset = 0, status, model } = {}) {
  const params = { limit, offset }
  if (status) params.status = status
  if (model) params.model = model

  const response = await api.get(API_ENDPOINTS.stats.logs, { params })
  return response.data
}

/**
 * Fetch model statistics.
 * @returns {Promise<Object>} Model stats
 */
export async function fetchModels() {
  const response = await api.get(API_ENDPOINTS.models)
  return response.data
}

/**
 * Fetch health status.
 * @returns {Promise<Object>} Health status
 */
export async function fetchHealth() {
  const response = await api.get(API_ENDPOINTS.health)
  return response.data
}

/**
 * Fetch current configuration.
 * @returns {Promise<Object>} Configuration data
 */
export async function fetchConfig() {
  const response = await api.get(API_ENDPOINTS.config)
  return response.data
}

/**
 * Update configuration.
 * @param {Object} config - Configuration updates
 * @returns {Promise<Object>} Updated configuration
 */
export async function updateConfig(config) {
  const response = await api.post(API_ENDPOINTS.config, config)
  return response.data
}

/**
 * Export logs to CSV.
 * @param {Object} filters - Filter parameters
 * @returns {Promise<Blob>} CSV file blob
 */
export async function exportLogsCSV(filters = {}) {
  // Fetch all logs matching filters
  const response = await fetchLogs({ limit: 10000, ...filters })

  // Convert to CSV
  const headers = ['Request ID', 'Timestamp', 'Model', 'Tokens', 'Latency (ms)', 'Status', 'Error']
  const rows = response.logs.map((log) => [
    log.request_id,
    log.timestamp,
    log.model,
    log.tokens,
    log.latency,
    log.status,
    log.error_message || '',
  ])

  const csv = [
    headers.join(','),
    ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
  ].join('\n')

  return new Blob([csv], { type: 'text/csv' })
}

// =============================================================================
// New Monitoring Endpoints
// =============================================================================

/**
 * Fetch GPU metrics.
 * @returns {Promise<Object>} GPU metrics data
 */
export async function fetchGPUMetrics() {
  const response = await api.get(API_ENDPOINTS.gpu)
  return response.data
}

/**
 * Fetch system CPU/RAM metrics.
 * @returns {Promise<Object>} System metrics data
 */
export async function fetchSystemMetrics() {
  const response = await api.get(API_ENDPOINTS.system.current)
  return response.data
}

/**
 * Fetch system metrics history for time-series charts.
 * @param {string} timeRange - Time range: 5m, 15m, 1h, 6h, 24h
 * @param {number} maxPoints - Maximum data points to return
 * @returns {Promise<Object>} System metrics history
 */
export async function fetchSystemMetricsHistory(timeRange = '1h', maxPoints = 100) {
  const response = await api.get(API_ENDPOINTS.system.history, {
    params: { time_range: timeRange, max_points: maxPoints },
  })
  return response.data
}

/**
 * Fetch enhanced stats with percentiles.
 * @returns {Promise<Object>} Enhanced stats with latency percentiles
 */
export async function fetchEnhancedStats() {
  const response = await api.get(API_ENDPOINTS.stats.enhanced)
  return response.data
}

/**
 * Fetch infrastructure health.
 * @returns {Promise<Object>} Infrastructure health status
 */
export async function fetchInfrastructureHealth() {
  const response = await api.get(API_ENDPOINTS.infrastructure)
  return response.data
}

export default api
