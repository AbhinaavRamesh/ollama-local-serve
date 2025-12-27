/**
 * Application constants and configuration values.
 */

// Time range options for charts
export const TIME_RANGES = {
  '1h': { label: '1 Hour', value: '1h', hours: 1 },
  '6h': { label: '6 Hours', value: '6h', hours: 6 },
  '24h': { label: '24 Hours', value: '24h', hours: 24 },
  '7d': { label: '7 Days', value: '7d', hours: 168 },
}

// Granularity options for time-series data
export const GRANULARITY = {
  '1m': { label: '1 Minute', value: '1m', minutes: 1 },
  '5m': { label: '5 Minutes', value: '5m', minutes: 5 },
  '1h': { label: '1 Hour', value: '1h', minutes: 60 },
}

// Status colors for different states
export const STATUS_COLORS = {
  success: {
    bg: 'bg-emerald-100 dark:bg-emerald-900/30',
    text: 'text-emerald-700 dark:text-emerald-400',
    border: 'border-emerald-200 dark:border-emerald-800',
    dot: 'bg-emerald-500',
  },
  error: {
    bg: 'bg-red-100 dark:bg-red-900/30',
    text: 'text-red-700 dark:text-red-400',
    border: 'border-red-200 dark:border-red-800',
    dot: 'bg-red-500',
  },
  warning: {
    bg: 'bg-amber-100 dark:bg-amber-900/30',
    text: 'text-amber-700 dark:text-amber-400',
    border: 'border-amber-200 dark:border-amber-800',
    dot: 'bg-amber-500',
  },
  info: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-700 dark:text-blue-400',
    border: 'border-blue-200 dark:border-blue-800',
    dot: 'bg-blue-500',
  },
  pending: {
    bg: 'bg-slate-100 dark:bg-slate-800/30',
    text: 'text-slate-700 dark:text-slate-400',
    border: 'border-slate-200 dark:border-slate-700',
    dot: 'bg-slate-500',
  },
}

// Health status mapping
export const HEALTH_STATUS = {
  healthy: {
    label: 'Healthy',
    color: 'success',
    description: 'All systems operational',
  },
  degraded: {
    label: 'Degraded',
    color: 'warning',
    description: 'Some services experiencing issues',
  },
  unhealthy: {
    label: 'Unhealthy',
    color: 'error',
    description: 'Service unavailable',
  },
}

// API endpoints (baseURL already includes /api prefix)
export const API_ENDPOINTS = {
  health: '/health',
  stats: {
    current: '/stats/current',
    history: '/stats/history',
    logs: '/stats/logs',
    enhanced: '/stats/enhanced',
  },
  models: '/models',
  config: '/config',
  // New monitoring endpoints
  gpu: '/gpu',
  system: {
    current: '/system',
    history: '/system/history',
  },
  infrastructure: '/infrastructure',
  metrics: '/metrics',
}

// Chart color palette
export const CHART_COLORS = {
  primary: 'hsl(221, 83%, 53%)',
  secondary: 'hsl(262, 83%, 58%)',
  success: 'hsl(142, 76%, 36%)',
  warning: 'hsl(38, 92%, 50%)',
  error: 'hsl(0, 84%, 60%)',
  info: 'hsl(199, 89%, 48%)',
  muted: 'hsl(215, 16%, 47%)',
  // Gradient colors for charts
  gradients: {
    blue: ['hsl(221, 83%, 53%)', 'hsl(221, 83%, 73%)'],
    purple: ['hsl(262, 83%, 58%)', 'hsl(262, 83%, 78%)'],
    green: ['hsl(142, 76%, 36%)', 'hsl(142, 76%, 56%)'],
  },
}

// Default refresh interval in milliseconds
export const DEFAULT_REFRESH_INTERVAL = 5000

// Pagination defaults
export const PAGINATION = {
  defaultPageSize: 25,
  pageSizeOptions: [10, 25, 50, 100],
}

// Navigation items
export const NAV_ITEMS = [
  { path: '/', label: 'Overview', icon: 'LayoutDashboard' },
  { path: '/system', label: 'System', icon: 'Cpu' },
  { path: '/performance', label: 'Performance', icon: 'Activity' },
  { path: '/logs', label: 'Logs', icon: 'ScrollText' },
  { path: '/models', label: 'Models', icon: 'Box' },
  { path: '/settings', label: 'Settings', icon: 'Settings' },
]

// Local storage keys
export const STORAGE_KEYS = {
  theme: 'ollama-monitor-theme',
  refreshInterval: 'ollama-monitor-refresh-interval',
  pageSize: 'ollama-monitor-page-size',
}
