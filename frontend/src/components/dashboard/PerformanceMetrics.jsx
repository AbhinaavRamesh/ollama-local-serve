/**
 * Performance Metrics panel showing Tokens/Second by model and Latency P50/P95/P99.
 */

import { clsx } from 'clsx'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { Zap, Clock, RefreshCw, AlertCircle, TrendingUp, Box } from 'lucide-react'
import { useFetchStats } from '../../hooks/useFetchStats'
import { useAutoRefresh } from '../../hooks/useAutoRefresh'
import { fetchEnhancedStats } from '../../utils/api'
import { formatNumber } from '../../utils/formatters'
import { CHART_COLORS } from '../../utils/constants'

/**
 * Latency gauge component showing P50, P95, P99.
 */
function LatencyGauge({ p50, p95, p99, loading = false }) {
  const maxLatency = Math.max(p99 * 1.2, 1000) // At least 1000ms scale

  // Define SLA thresholds
  const thresholds = {
    good: 500,    // < 500ms is good
    warning: 2000, // < 2000ms is warning
    // > 2000ms is bad
  }

  const getColor = (value) => {
    if (value < thresholds.good) return 'text-emerald-500'
    if (value < thresholds.warning) return 'text-amber-500'
    return 'text-red-500'
  }

  const getBgColor = (value) => {
    if (value < thresholds.good) return 'bg-emerald-500'
    if (value < thresholds.warning) return 'bg-amber-500'
    return 'bg-red-500'
  }

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="space-y-2">
            <div className="h-4 w-16 bg-slate-300 dark:bg-slate-600 rounded" />
            <div className="h-2 bg-slate-300 dark:bg-slate-600 rounded" />
          </div>
        ))}
      </div>
    )
  }

  const percentiles = [
    { label: 'P50', value: p50, description: 'Median latency' },
    { label: 'P95', value: p95, description: '95th percentile' },
    { label: 'P99', value: p99, description: '99th percentile' },
  ]

  return (
    <div className="space-y-4">
      {percentiles.map(({ label, value, description }) => (
        <div key={label} className="space-y-1">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
                {label}
              </span>
              <span className={clsx('text-sm font-bold', getColor(value))}>
                {formatNumber(value, 0)} ms
              </span>
            </div>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {description}
            </span>
          </div>
          <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className={clsx(
                'h-full rounded-full transition-all duration-500',
                getBgColor(value)
              )}
              style={{ width: `${Math.min((value / maxLatency) * 100, 100)}%` }}
            />
          </div>
        </div>
      ))}

      {/* Legend */}
      <div className="flex items-center gap-4 pt-2 text-xs text-slate-500 dark:text-slate-400">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <span>&lt; 500ms</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-amber-500" />
          <span>500-2000ms</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span>&gt; 2000ms</span>
        </div>
      </div>
    </div>
  )
}

/**
 * Tokens per second bar chart by model.
 */
function TokensPerSecondChart({ models, loading = false }) {
  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    )
  }

  if (!models || Object.keys(models).length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500 dark:text-slate-400">
        <div className="text-center">
          <Box className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No model data available</p>
        </div>
      </div>
    )
  }

  // Transform data for chart
  const chartData = Object.entries(models)
    .map(([name, stats]) => ({
      name: name.split(':')[0], // Truncate version tag
      fullName: name,
      tokensPerSec: stats.tokens_per_second || 0,
      totalTokens: stats.total_tokens || 0,
      requests: stats.request_count || 0,
    }))
    .sort((a, b) => b.tokensPerSec - a.tokensPerSec)
    .slice(0, 8) // Top 8 models

  const colors = [
    CHART_COLORS.primary,
    CHART_COLORS.secondary,
    CHART_COLORS.success,
    CHART_COLORS.info,
    CHART_COLORS.warning,
    CHART_COLORS.muted,
    'hsl(280, 60%, 50%)',
    'hsl(320, 60%, 50%)',
  ]

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
          <XAxis
            type="number"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            axisLine={{ stroke: '#374151' }}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            axisLine={{ stroke: '#374151' }}
            width={80}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#F9FAFB' }}
            formatter={(value, name, props) => [
              `${formatNumber(value, 1)} tokens/s`,
              props.payload.fullName,
            ]}
          />
          <Bar dataKey="tokensPerSec" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={entry.name} fill={colors[index % colors.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/**
 * Performance Metrics component.
 */
export function PerformanceMetrics({ refreshInterval = 5000 }) {
  // Fetch enhanced stats
  const {
    data: statsData,
    loading,
    error,
    refetch,
  } = useFetchStats(() => fetchEnhancedStats(), { staleTime: 3000 })

  // Auto-refresh
  useAutoRefresh(refetch, refreshInterval)

  // Extract values
  const models = statsData?.models ?? {}
  const tokensPerSec = statsData?.tokens_per_second ?? 0
  const p50 = statsData?.latency_p50_ms ?? 0
  const p95 = statsData?.latency_p95_ms ?? 0
  const p99 = statsData?.latency_p99_ms ?? 0

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Tokens Per Second Panel */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Tokens/Second
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <span className="text-2xl font-bold text-amber-500">
                {formatNumber(tokensPerSec, 1)}
              </span>
              <span className="text-sm text-slate-500 dark:text-slate-400 ml-1">/s</span>
            </div>
            <button
              onClick={refetch}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={clsx('w-4 h-4 text-slate-500', loading && 'animate-spin')} />
            </button>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="px-6 py-4 bg-red-50 dark:bg-red-900/20">
            <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">Failed to load metrics</span>
            </div>
          </div>
        )}

        {/* Chart */}
        <div className="p-6">
          <TokensPerSecondChart models={models} loading={loading} />
        </div>
      </div>

      {/* Latency Percentiles Panel */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-blue-500" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Request Latency
            </h2>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <TrendingUp className="w-4 h-4" />
            <span>Percentiles</span>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="px-6 py-4 bg-red-50 dark:bg-red-900/20">
            <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">Failed to load metrics</span>
            </div>
          </div>
        )}

        {/* Latency Gauges */}
        <div className="p-6">
          <LatencyGauge p50={p50} p95={p95} p99={p99} loading={loading} />

          {/* Summary Stats */}
          <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">
                  {formatNumber(statsData?.total_requests ?? 0)}
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  Total Requests
                </div>
              </div>
              <div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">
                  {formatNumber(statsData?.total_tokens ?? 0)}
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  Total Tokens
                </div>
              </div>
              <div>
                <div className={clsx(
                  'text-2xl font-bold',
                  (statsData?.error_rate_percent ?? 0) > 5
                    ? 'text-red-500'
                    : 'text-emerald-500'
                )}>
                  {(statsData?.error_rate_percent ?? 0).toFixed(1)}%
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  Error Rate
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PerformanceMetrics
