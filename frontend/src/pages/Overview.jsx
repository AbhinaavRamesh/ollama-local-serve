/**
 * Overview page - main dashboard with key metrics.
 */

import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Activity, Zap, Clock, AlertTriangle, RefreshCw } from 'lucide-react'
import { StatsCard, StatsCardGrid } from '../components/dashboard/StatsCard'
import { KPICard } from '../components/dashboard/KPICard'
import { TrendChart } from '../components/charts/TrendChart'
import { LatencyChart } from '../components/charts/LatencyChart'
import { StatusIndicator } from '../components/dashboard/StatusIndicator'
import { PageSkeleton } from '../components/ui/LoadingSkeleton'
import { ErrorState } from '../components/ui/EmptyState'
// New enhanced dashboard components
import { SystemOverview } from '../components/dashboard/SystemOverview'
import { PerformanceMetrics } from '../components/dashboard/PerformanceMetrics'
import { InfrastructureHealth } from '../components/dashboard/InfrastructureHealth'
import { useFetchStats } from '../hooks/useFetchStats'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { useAppContext } from '../context/AppContext'
import { fetchCurrentStats, fetchStatsHistory } from '../utils/api'
import { formatUptime, formatNumber, formatRelativeTime } from '../utils/formatters'
import { HEALTH_STATUS } from '../utils/constants'

/**
 * Overview dashboard page.
 */
export function Overview() {
  const [timeRange, setTimeRange] = useState('1h')
  const { serviceStatus, refreshInterval, lastRefresh } = useAppContext()

  // Fetch current stats
  const {
    data: stats,
    loading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useFetchStats(() => fetchCurrentStats(), {
    staleTime: 5000,
  })

  // Fetch history for charts
  const {
    data: history,
    loading: historyLoading,
    refetch: refetchHistory,
  } = useFetchStats(
    () => fetchStatsHistory(timeRange, '1m'),
    {
      staleTime: 10000,
      deps: [timeRange],
    }
  )

  // Auto-refresh
  useAutoRefresh(
    useCallback(() => {
      refetchStats()
      refetchHistory()
    }, [refetchStats, refetchHistory]),
    refreshInterval
  )

  // Handle time range change
  const handleTimeRangeChange = (range) => {
    setTimeRange(range)
  }

  // Prepare chart data
  const chartData = history?.data?.map((point) => ({
    timestamp: point.timestamp,
    tokens: point.tokens_total,
    latency: point.latency_ms,
    throughput: point.throughput,
    p50: point.latency_ms * 0.5,
    p95: point.latency_ms * 0.95,
    p99: point.latency_ms,
  })) || []

  // Generate sparkline data
  const sparklineData = chartData.slice(-20).map((p) => p.tokens)

  if (statsError) {
    return <ErrorState message={statsError.message} onRetry={refetchStats} />
  }

  const statusConfig = HEALTH_STATUS[serviceStatus.status] || HEALTH_STATUS.unhealthy

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
            Overview
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Monitor your Ollama service performance
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm text-slate-500 dark:text-slate-400">
            Updated {formatRelativeTime(lastRefresh)}
          </div>
        </div>
      </div>

      {/* Service Status Banner */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <StatusIndicator
              status={statusConfig.color}
              label={statusConfig.label}
              pulse={serviceStatus.status === 'healthy'}
              size="lg"
            />
            <div className="border-l border-slate-200 dark:border-slate-700 pl-4">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {statusConfig.description}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="text-slate-500 dark:text-slate-400">Uptime: </span>
              <span className="font-medium text-slate-900 dark:text-white">
                {formatUptime(serviceStatus.uptime)}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Database: </span>
              <span
                className={
                  serviceStatus.databaseConnected
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-red-600 dark:text-red-400'
                }
              >
                {serviceStatus.databaseConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Tokens"
          value={stats?.tokens_total || 0}
          unit="tokens"
          subtitle="All-time generated"
          sparklineData={sparklineData}
          color="primary"
          loading={statsLoading}
          href="/performance"
        />
        <KPICard
          title="Tokens/Second"
          value={stats?.tokens_per_sec || 0}
          unit="/s"
          subtitle="Last hour average"
          color="success"
          loading={statsLoading}
          href="/performance"
        />
        <KPICard
          title="Uptime"
          value={stats?.uptime_hours || 0}
          unit="hours"
          subtitle="Since last restart"
          color="primary"
          loading={statsLoading}
        />
        <KPICard
          title="Errors"
          value={stats?.error_count || 0}
          subtitle="Total error count"
          color={stats?.error_count > 0 ? 'error' : 'success'}
          loading={statsLoading}
          href="/logs"
        />
      </div>

      {/* Stats Cards (Alternative View) */}
      <StatsCardGrid>
        <StatsCard
          title="Total Requests"
          value={stats?.request_count || 0}
          icon="Activity"
          loading={statsLoading}
          href="/logs"
        />
        <StatsCard
          title="Avg Latency"
          value={stats?.avg_latency_ms || 0}
          unit="ms"
          icon="Clock"
          loading={statsLoading}
          href="/performance"
        />
        <StatsCard
          title="Models Available"
          value={stats?.models_available || 0}
          icon="Box"
          loading={statsLoading}
          href="/models"
        />
        <StatsCard
          title="Error Rate"
          value={
            stats?.request_count > 0
              ? ((stats?.error_count / stats?.request_count) * 100).toFixed(2)
              : 0
          }
          unit="%"
          icon="AlertTriangle"
          loading={statsLoading}
          href="/logs"
        />
      </StatsCardGrid>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TrendChart
          title="Tokens Generated"
          data={chartData}
          xKey="timestamp"
          yKey="tokens"
          yLabel="Tokens"
          timeRange={timeRange}
          onTimeRangeChange={handleTimeRangeChange}
          loading={historyLoading}
        />
        <LatencyChart
          data={chartData}
          loading={historyLoading}
          slaTarget={500}
        />
      </div>

      {/* System Overview Section */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">
          System Metrics
        </h2>
        <SystemOverview refreshInterval={refreshInterval} />
      </div>

      {/* Performance Metrics Section */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">
          Performance Metrics
        </h2>
        <PerformanceMetrics refreshInterval={refreshInterval} />
      </div>

      {/* Infrastructure Health Section */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">
          Infrastructure Health
        </h2>
        <InfrastructureHealth refreshInterval={refreshInterval * 2} />
      </div>
    </motion.div>
  )
}

export default Overview
