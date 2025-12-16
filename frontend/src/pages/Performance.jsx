/**
 * Performance page - detailed analytics and metrics.
 */

import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { TrendChart } from '../components/charts/TrendChart'
import { LatencyChart } from '../components/charts/LatencyChart'
import { ThroughputChart } from '../components/charts/ThroughputChart'
import { ModelComparison } from '../components/tables/ModelComparison'
import { KPICard } from '../components/dashboard/KPICard'
import { PageSkeleton } from '../components/ui/LoadingSkeleton'
import { ErrorState } from '../components/ui/EmptyState'
import { useFetchStats } from '../hooks/useFetchStats'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { useAppContext } from '../context/AppContext'
import { fetchStatsHistory, fetchModels, fetchCurrentStats } from '../utils/api'
import { TIME_RANGES } from '../utils/constants'

/**
 * Performance analytics page.
 */
export function Performance() {
  const [timeRange, setTimeRange] = useState('1h')
  const { refreshInterval } = useAppContext()

  // Fetch current stats
  const {
    data: stats,
    loading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useFetchStats(() => fetchCurrentStats(), {
    staleTime: 5000,
  })

  // Fetch history
  const {
    data: history,
    loading: historyLoading,
    error: historyError,
    refetch: refetchHistory,
  } = useFetchStats(
    () => fetchStatsHistory(timeRange, '1m'),
    {
      staleTime: 10000,
      deps: [timeRange],
    }
  )

  // Fetch models
  const {
    data: modelsData,
    loading: modelsLoading,
    refetch: refetchModels,
  } = useFetchStats(() => fetchModels(), {
    staleTime: 30000,
  })

  // Auto-refresh
  useAutoRefresh(
    useCallback(() => {
      refetchStats()
      refetchHistory()
      refetchModels()
    }, [refetchStats, refetchHistory, refetchModels]),
    refreshInterval
  )

  // Prepare chart data
  const chartData = history?.data?.map((point) => ({
    timestamp: point.timestamp,
    tokens: point.tokens_total,
    latency: point.latency_ms,
    throughput: point.throughput,
    requests: Math.floor(point.throughput * 60), // Convert to per minute
    tokensPerSec: point.tokens_total / 60,
    p50: point.latency_ms * 0.5,
    p95: point.latency_ms * 0.95,
    p99: point.latency_ms,
    errors: point.error_count,
  })) || []

  if (statsError || historyError) {
    return (
      <ErrorState
        message={statsError?.message || historyError?.message}
        onRetry={() => {
          refetchStats()
          refetchHistory()
        }}
      />
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Performance
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Detailed performance analytics and model comparison
          </p>
        </div>
        <div className="flex items-center gap-2">
          {Object.entries(TIME_RANGES).map(([key, config]) => (
            <button
              key={key}
              onClick={() => setTimeRange(key)}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                timeRange === key
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              {config.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Avg Latency"
          value={stats?.avg_latency_ms || 0}
          unit="ms"
          subtitle="Average response time"
          color={stats?.avg_latency_ms > 500 ? 'warning' : 'success'}
          loading={statsLoading}
        />
        <KPICard
          title="Throughput"
          value={stats?.tokens_per_sec || 0}
          unit="tokens/s"
          subtitle="Current throughput"
          color="primary"
          loading={statsLoading}
        />
        <KPICard
          title="Total Requests"
          value={stats?.request_count || 0}
          subtitle="All time"
          color="primary"
          loading={statsLoading}
        />
        <KPICard
          title="Error Rate"
          value={
            stats?.request_count > 0
              ? (stats?.error_count / stats?.request_count) * 100
              : 0
          }
          unit="%"
          subtitle="Failure rate"
          color={stats?.error_count > 0 ? 'error' : 'success'}
          loading={statsLoading}
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ThroughputChart
          data={chartData}
          loading={historyLoading}
        />
        <LatencyChart
          data={chartData}
          loading={historyLoading}
          slaTarget={500}
        />
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TrendChart
          title="Tokens Generated"
          data={chartData}
          xKey="timestamp"
          yKey="tokens"
          yLabel="Total tokens"
          loading={historyLoading}
        />
        <TrendChart
          title="Error Count"
          data={chartData}
          xKey="timestamp"
          yKey="errors"
          yLabel="Errors"
          color="hsl(0, 84%, 60%)"
          loading={historyLoading}
        />
      </div>

      {/* Model Performance */}
      <ModelComparison
        models={modelsData?.models || []}
        loading={modelsLoading}
      />
    </motion.div>
  )
}

export default Performance
