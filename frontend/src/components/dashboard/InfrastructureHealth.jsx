/**
 * Infrastructure Health panel showing Pod Status, GPU Temps, VRAM/Pod, Errors.
 */

import { clsx } from 'clsx'
import {
  Server,
  Thermometer,
  HardDrive,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  AlertCircle,
  Activity,
} from 'lucide-react'
import { useFetchStats } from '../../hooks/useFetchStats'
import { useAutoRefresh } from '../../hooks/useAutoRefresh'
import { fetchInfrastructureHealth } from '../../utils/api'
import { formatNumber, formatRelativeTime } from '../../utils/formatters'

/**
 * Service status indicator.
 */
function ServiceStatus({ name, status, latency, message }) {
  const statusConfig = {
    healthy: {
      icon: CheckCircle,
      color: 'text-emerald-500',
      bg: 'bg-emerald-100 dark:bg-emerald-900/30',
      label: 'Healthy',
    },
    degraded: {
      icon: AlertTriangle,
      color: 'text-amber-500',
      bg: 'bg-amber-100 dark:bg-amber-900/30',
      label: 'Degraded',
    },
    unhealthy: {
      icon: XCircle,
      color: 'text-red-500',
      bg: 'bg-red-100 dark:bg-red-900/30',
      label: 'Unhealthy',
    },
  }

  const config = statusConfig[status] || statusConfig.unhealthy
  const Icon = config.icon

  return (
    <div className={clsx(
      'flex items-center justify-between p-3 rounded-lg',
      config.bg
    )}>
      <div className="flex items-center gap-3">
        <Icon className={clsx('w-5 h-5', config.color)} />
        <div>
          <div className="font-medium text-slate-900 dark:text-white capitalize">
            {name}
          </div>
          {message && (
            <div className="text-xs text-slate-500 dark:text-slate-400">
              {message}
            </div>
          )}
        </div>
      </div>
      <div className="text-right">
        <div className={clsx('text-sm font-medium', config.color)}>
          {config.label}
        </div>
        {latency !== null && latency !== undefined && (
          <div className="text-xs text-slate-500 dark:text-slate-400">
            {latency.toFixed(0)}ms
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Metric card for infrastructure stats.
 */
function InfraMetricCard({ icon: Icon, label, value, unit, status = 'normal', description }) {
  const statusColors = {
    normal: 'text-slate-900 dark:text-white',
    good: 'text-emerald-500',
    warning: 'text-amber-500',
    critical: 'text-red-500',
  }

  return (
    <div className="flex items-center gap-4 p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
      <div className="p-3 rounded-full bg-slate-200 dark:bg-slate-700">
        <Icon className="w-5 h-5 text-slate-600 dark:text-slate-400" />
      </div>
      <div className="flex-1">
        <div className="text-sm text-slate-500 dark:text-slate-400">
          {label}
        </div>
        <div className="flex items-baseline gap-1">
          <span className={clsx('text-xl font-bold', statusColors[status])}>
            {typeof value === 'number' ? formatNumber(value, value < 10 ? 1 : 0) : value}
          </span>
          {unit && (
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {unit}
            </span>
          )}
        </div>
        {description && (
          <div className="text-xs text-slate-500 dark:text-slate-400">
            {description}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Overall status banner.
 */
function StatusBanner({ status, timestamp }) {
  const statusConfig = {
    healthy: {
      icon: CheckCircle,
      color: 'text-emerald-500',
      bg: 'bg-emerald-50 dark:bg-emerald-900/20',
      border: 'border-emerald-200 dark:border-emerald-800',
      label: 'All Systems Operational',
    },
    degraded: {
      icon: AlertTriangle,
      color: 'text-amber-500',
      bg: 'bg-amber-50 dark:bg-amber-900/20',
      border: 'border-amber-200 dark:border-amber-800',
      label: 'Some Services Degraded',
    },
    unhealthy: {
      icon: XCircle,
      color: 'text-red-500',
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-200 dark:border-red-800',
      label: 'System Issues Detected',
    },
  }

  const config = statusConfig[status] || statusConfig.unhealthy
  const Icon = config.icon

  return (
    <div className={clsx(
      'flex items-center justify-between p-4 rounded-lg border',
      config.bg,
      config.border
    )}>
      <div className="flex items-center gap-3">
        <Icon className={clsx('w-6 h-6', config.color)} />
        <div>
          <div className={clsx('font-semibold', config.color)}>
            {config.label}
          </div>
          {timestamp && (
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Last checked: {formatRelativeTime(timestamp)}
            </div>
          )}
        </div>
      </div>
      <div className={clsx(
        'px-3 py-1 rounded-full text-sm font-medium',
        config.bg,
        config.color
      )}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </div>
    </div>
  )
}

/**
 * Infrastructure Health component.
 */
export function InfrastructureHealth({ refreshInterval = 10000 }) {
  // Fetch infrastructure health
  const {
    data: healthData,
    loading,
    error,
    refetch,
  } = useFetchStats(() => fetchInfrastructureHealth(), { staleTime: 5000 })

  // Auto-refresh
  useAutoRefresh(refetch, refreshInterval)

  // Extract values with defaults
  const overallStatus = healthData?.overall_status ?? 'unhealthy'
  const timestamp = healthData?.timestamp
  const services = healthData?.services ?? []
  const gpuAvailable = healthData?.gpu_available ?? false
  const gpuTemp = healthData?.gpu_temperature_celsius ?? 0
  const vramUsed = healthData?.vram_used_gb ?? 0
  const vramTotal = healthData?.vram_total_gb ?? 0
  const queueDepth = healthData?.queue_depth ?? 0
  const errorCount24h = healthData?.error_count_24h ?? 0
  const errorRate24h = healthData?.error_rate_24h_percent ?? 0
  const activeModels = healthData?.active_models ?? []
  const loadedModels = healthData?.loaded_models_count ?? 0

  // Determine temperature status
  const getTempStatus = (temp) => {
    if (temp < 60) return 'good'
    if (temp < 80) return 'warning'
    return 'critical'
  }

  // Determine error rate status
  const getErrorStatus = (rate) => {
    if (rate < 1) return 'good'
    if (rate < 5) return 'warning'
    return 'critical'
  }

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-slate-500" />
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            Infrastructure Health
          </h2>
        </div>
        <button
          onClick={refetch}
          className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          title="Refresh"
        >
          <RefreshCw className={clsx('w-4 h-4 text-slate-500', loading && 'animate-spin')} />
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="px-6 py-4 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">Failed to load infrastructure health</span>
          </div>
        </div>
      )}

      <div className="p-6 space-y-6">
        {/* Overall Status Banner */}
        <StatusBanner status={overallStatus} timestamp={timestamp} />

        {/* Services Grid */}
        <div>
          <h3 className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-3">
            Service Status
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {services.map((service) => (
              <ServiceStatus
                key={service.name}
                name={service.name}
                status={service.status}
                latency={service.latency_ms}
                message={service.message}
              />
            ))}
          </div>
        </div>

        {/* Infrastructure Metrics Grid */}
        <div>
          <h3 className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-3">
            Resource Metrics
          </h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {/* GPU Temperature */}
            <InfraMetricCard
              icon={Thermometer}
              label="GPU Temp"
              value={gpuAvailable ? gpuTemp : 'N/A'}
              unit={gpuAvailable ? '°C' : ''}
              status={gpuAvailable ? getTempStatus(gpuTemp) : 'normal'}
              description={gpuAvailable ? (gpuTemp > 80 ? 'High temperature!' : 'Normal') : 'GPU not detected'}
            />

            {/* VRAM Usage */}
            <InfraMetricCard
              icon={HardDrive}
              label="VRAM"
              value={gpuAvailable ? vramUsed : 'N/A'}
              unit={gpuAvailable ? `/ ${vramTotal.toFixed(0)} GB` : ''}
              status="normal"
              description={gpuAvailable ? `${((vramUsed / vramTotal) * 100).toFixed(0)}% used` : 'Not available'}
            />

            {/* Queue Depth */}
            <InfraMetricCard
              icon={Activity}
              label="Queue"
              value={queueDepth}
              unit="requests"
              status={queueDepth > 10 ? 'critical' : queueDepth > 5 ? 'warning' : 'good'}
              description="Pending in queue"
            />

            {/* Errors (24h) */}
            <InfraMetricCard
              icon={AlertTriangle}
              label="Errors (24h)"
              value={errorCount24h}
              unit=""
              status={getErrorStatus(errorRate24h)}
              description={`${errorRate24h.toFixed(2)}% error rate`}
            />
          </div>
        </div>

        {/* Models Info */}
        <div className="flex items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
          <div>
            <div className="text-sm text-slate-500 dark:text-slate-400">
              Loaded Models
            </div>
            <div className="text-xl font-bold text-slate-900 dark:text-white">
              {loadedModels}
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-slate-500 dark:text-slate-400">
              Active Models
            </div>
            <div className="flex flex-wrap gap-1 justify-end mt-1">
              {activeModels.length > 0 ? (
                activeModels.slice(0, 3).map((model) => (
                  <span
                    key={model}
                    className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
                  >
                    {model.split(':')[0]}
                  </span>
                ))
              ) : (
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  None active
                </span>
              )}
              {activeModels.length > 3 && (
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  +{activeModels.length - 3} more
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default InfrastructureHealth
