/**
 * System Overview panel showing GPU, VRAM, Queue, and Active Models.
 */

import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { Cpu, HardDrive, ListOrdered, Box, RefreshCw, AlertCircle, MemoryStick, Activity } from 'lucide-react'
import { useFetchStats } from '../../hooks/useFetchStats'
import { useAutoRefresh } from '../../hooks/useAutoRefresh'
import { fetchGPUMetrics, fetchEnhancedStats, fetchSystemMetrics } from '../../utils/api'
import { formatNumber } from '../../utils/formatters'

/**
 * Metric tile component for displaying a single metric.
 */
function MetricTile({ icon: Icon, label, value, unit, subtext, color = 'blue', loading = false, href }) {
  const colorClasses = {
    blue: {
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      icon: 'text-blue-500 dark:text-blue-400',
      value: 'text-blue-600 dark:text-blue-400',
    },
    green: {
      bg: 'bg-emerald-50 dark:bg-emerald-900/20',
      icon: 'text-emerald-500 dark:text-emerald-400',
      value: 'text-emerald-600 dark:text-emerald-400',
    },
    purple: {
      bg: 'bg-purple-50 dark:bg-purple-900/20',
      icon: 'text-purple-500 dark:text-purple-400',
      value: 'text-purple-600 dark:text-purple-400',
    },
    amber: {
      bg: 'bg-amber-50 dark:bg-amber-900/20',
      icon: 'text-amber-500 dark:text-amber-400',
      value: 'text-amber-600 dark:text-amber-400',
    },
    red: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      icon: 'text-red-500 dark:text-red-400',
      value: 'text-red-600 dark:text-red-400',
    },
  }

  const colors = colorClasses[color] || colorClasses.blue

  if (loading) {
    return (
      <div className={clsx(
        'rounded-lg p-4 animate-pulse',
        colors.bg
      )}>
        <div className="h-4 w-20 bg-slate-300 dark:bg-slate-600 rounded mb-2" />
        <div className="h-8 w-24 bg-slate-300 dark:bg-slate-600 rounded" />
      </div>
    )
  }

  const content = (
    <div className={clsx(
      'rounded-lg p-4 transition-all hover:shadow-md',
      colors.bg,
      href && 'cursor-pointer hover:ring-2 hover:ring-offset-2 hover:ring-blue-500 dark:hover:ring-offset-slate-900'
    )}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={clsx('w-4 h-4', colors.icon)} />
        <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
          {label}
        </span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className={clsx('text-2xl font-bold', colors.value)}>
          {typeof value === 'number' ? formatNumber(value, value < 10 ? 1 : 0) : value}
        </span>
        {unit && (
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {unit}
          </span>
        )}
      </div>
      {subtext && (
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          {subtext}
        </p>
      )}
    </div>
  )

  if (href) {
    return <Link to={href}>{content}</Link>
  }

  return content
}

/**
 * Progress bar component for utilization metrics.
 */
function ProgressBar({ value, max = 100, color = 'blue', showLabel = true }) {
  const percentage = Math.min((value / max) * 100, 100)

  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-emerald-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500',
  }

  // Determine color based on percentage
  let barColor = colorClasses[color]
  if (percentage > 90) barColor = colorClasses.red
  else if (percentage > 70) barColor = colorClasses.amber

  return (
    <div className="w-full">
      <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-500', barColor)}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-1">
          <span>{value.toFixed(1)}</span>
          <span>{max}</span>
        </div>
      )}
    </div>
  )
}

/**
 * System Overview component.
 */
export function SystemOverview({ refreshInterval = 5000 }) {
  // Fetch GPU metrics
  const {
    data: gpuData,
    loading: gpuLoading,
    error: gpuError,
    refetch: refetchGPU,
  } = useFetchStats(() => fetchGPUMetrics(), { staleTime: 3000 })

  // Fetch system metrics (CPU/RAM)
  const {
    data: systemData,
    loading: systemLoading,
    error: systemError,
    refetch: refetchSystem,
  } = useFetchStats(() => fetchSystemMetrics(), { staleTime: 3000 })

  // Fetch enhanced stats
  const {
    data: statsData,
    loading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useFetchStats(() => fetchEnhancedStats(), { staleTime: 3000 })

  // Auto-refresh
  useAutoRefresh(
    useCallback(() => {
      refetchGPU()
      refetchSystem()
      refetchStats()
    }, [refetchGPU, refetchSystem, refetchStats]),
    refreshInterval
  )

  const loading = gpuLoading || systemLoading || statsLoading
  const error = gpuError || systemError || statsError

  // Extract GPU values
  const gpuAvailable = gpuData?.available ?? false
  const gpuUtilization = gpuData?.avg_gpu_utilization_percent ?? 0
  const vramUsed = gpuData?.used_vram_gb ?? 0
  const vramTotal = gpuData?.total_vram_gb ?? 0
  const gpuTemp = gpuData?.avg_temperature_celsius ?? 0

  // Extract system values (CPU/RAM)
  const cpuPercent = systemData?.cpu_percent ?? 0
  const memoryPercent = systemData?.memory_percent ?? 0
  const memoryUsed = systemData?.memory_used_gb ?? 0
  const memoryTotal = systemData?.memory_total_gb ?? 0
  const cpuCount = systemData?.cpu_count_logical ?? 0

  // Extract stats values
  const queueDepth = statsData?.queue_depth ?? 0
  const activeModels = statsData?.active_models ?? []

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          System Overview
        </h2>
        <button
          onClick={() => { refetchGPU(); refetchSystem(); refetchStats(); }}
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
            <span className="text-sm">Failed to load system metrics</span>
          </div>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 p-6">
        {/* CPU Usage */}
        <MetricTile
          icon={Activity}
          label="CPU"
          value={cpuPercent}
          unit="%"
          subtext={`${cpuCount} cores`}
          color={cpuPercent > 80 ? 'red' : cpuPercent > 50 ? 'amber' : 'green'}
          loading={loading}
          href="/system?section=cpu_percent"
        />

        {/* RAM Usage */}
        <MetricTile
          icon={MemoryStick}
          label="RAM"
          value={memoryUsed}
          unit="GB"
          subtext={`${memoryPercent.toFixed(0)}% of ${memoryTotal.toFixed(0)} GB`}
          color={memoryPercent > 80 ? 'red' : memoryPercent > 60 ? 'amber' : 'green'}
          loading={loading}
          href="/system?section=memory_percent"
        />

        {/* GPU Utilization */}
        <MetricTile
          icon={Cpu}
          label="GPU Util"
          value={gpuAvailable ? gpuUtilization : 'N/A'}
          unit={gpuAvailable ? '%' : ''}
          subtext={gpuAvailable ? `${gpuTemp}°C` : 'GPU not detected'}
          color={gpuAvailable ? (gpuUtilization > 80 ? 'red' : gpuUtilization > 50 ? 'amber' : 'green') : 'blue'}
          loading={loading}
          href="/system?section=gpu_utilization_percent"
        />

        {/* VRAM Used */}
        <MetricTile
          icon={HardDrive}
          label="VRAM"
          value={gpuAvailable ? vramUsed : 'N/A'}
          unit={gpuAvailable ? 'GB' : ''}
          subtext={gpuAvailable ? `of ${vramTotal.toFixed(1)} GB` : 'Not available'}
          color="purple"
          loading={loading}
          href="/system?section=vram_used_gb"
        />

        {/* Queue Depth */}
        <MetricTile
          icon={ListOrdered}
          label="Queue"
          value={queueDepth}
          unit=""
          subtext="pending requests"
          color={queueDepth > 10 ? 'red' : queueDepth > 5 ? 'amber' : 'green'}
          loading={loading}
          href="/system?section=queue_depth"
        />

        {/* Active Models */}
        <MetricTile
          icon={Box}
          label="Models"
          value={activeModels.length}
          unit=""
          subtext={activeModels.length > 0 ? activeModels.slice(0, 2).join(', ') : 'No active'}
          color="blue"
          loading={loading}
          href="/models"
        />
      </div>

      {/* RAM Progress Bar */}
      <div className="px-6 pb-4">
        <div className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">
          RAM Utilization ({memoryPercent.toFixed(0)}%)
        </div>
        <ProgressBar value={memoryUsed} max={memoryTotal} color="green" />
      </div>

      {/* GPU VRAM Progress Bar */}
      {gpuAvailable && (
        <div className="px-6 pb-6">
          <div className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">
            VRAM Utilization
          </div>
          <ProgressBar value={vramUsed} max={vramTotal} color="blue" />
        </div>
      )}

      {/* Active Models List */}
      {activeModels.length > 0 && (
        <div className="px-6 pb-6">
          <div className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">
            Active Models
          </div>
          <div className="flex flex-wrap gap-2">
            {activeModels.map((model) => (
              <span
                key={model}
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
              >
                {model}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default SystemOverview
