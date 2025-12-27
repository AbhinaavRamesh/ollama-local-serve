/**
 * System page - detailed system metrics with time-series charts.
 */

import { useState, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import {
  Cpu,
  MemoryStick,
  HardDrive,
  Thermometer,
  Activity,
  ListOrdered,
  RefreshCw,
} from 'lucide-react'
import { KPICard } from '../components/dashboard/KPICard'
import { ErrorState } from '../components/ui/EmptyState'
import { useFetchStats } from '../hooks/useFetchStats'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { useAppContext } from '../context/AppContext'
import {
  fetchSystemMetrics,
  fetchSystemMetricsHistory,
  fetchGPUMetrics,
} from '../utils/api'
import { formatNumber } from '../utils/formatters'
import { CHART_COLORS } from '../utils/constants'

// Time range options for system metrics
const SYSTEM_TIME_RANGES = {
  '5m': { label: '5m', seconds: 5 * 60 },
  '15m': { label: '15m', seconds: 15 * 60 },
  '1h': { label: '1h', seconds: 60 * 60 },
  '6h': { label: '6h', seconds: 6 * 60 * 60 },
  '24h': { label: '24h', seconds: 24 * 60 * 60 },
}

/**
 * Custom tooltip for charts.
 */
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg p-3">
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">
        {typeof label === 'string' && label.includes('T')
          ? format(parseISO(label), 'MMM d, HH:mm:ss')
          : label}
      </p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-sm text-slate-600 dark:text-slate-300">
            {entry.name}:
          </span>
          <span className="text-sm font-medium text-slate-900 dark:text-white">
            {formatNumber(entry.value, 1)}{entry.unit || ''}
          </span>
        </div>
      ))}
    </div>
  )
}

/**
 * System metric chart component.
 */
function MetricChart({
  title,
  data,
  dataKey,
  color = CHART_COLORS.primary,
  unit = '',
  icon: Icon,
  loading = false,
  yDomain,
}) {
  const formatXAxis = (value) => {
    if (!value) return ''
    try {
      const date = typeof value === 'string' ? parseISO(value) : value
      return format(date, 'HH:mm')
    } catch {
      return value
    }
  }

  const gradientId = `gradient-${dataKey}`

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
        <div className="animate-pulse">
          <div className="h-4 w-32 bg-slate-300 dark:bg-slate-600 rounded mb-4" />
          <div className="h-48 bg-slate-200 dark:bg-slate-700 rounded" />
        </div>
      </div>
    )
  }

  // Get current value (last data point)
  const currentValue = data.length > 0 ? data[data.length - 1][dataKey] : 0

  return (
    <div
      id={`chart-${dataKey}`}
      className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-700">
              <Icon className="w-5 h-5 text-slate-600 dark:text-slate-400" />
            </div>
          )}
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">
              {title}
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Current: <span className="font-medium" style={{ color }}>{formatNumber(currentValue, 1)}{unit}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="currentColor"
              className="text-slate-200 dark:text-slate-700"
            />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatXAxis}
              tick={{ fontSize: 10 }}
              stroke="currentColor"
              className="text-slate-400"
            />
            <YAxis
              tickFormatter={(value) => `${formatNumber(value, 0)}${unit}`}
              tick={{ fontSize: 10 }}
              stroke="currentColor"
              className="text-slate-400"
              width={45}
              domain={yDomain}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey={dataKey}
              name={title}
              stroke={color}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
              unit={unit}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/**
 * System metrics page.
 */
export function System() {
  const [searchParams] = useSearchParams()
  const initialSection = searchParams.get('section') || 'cpu'
  const [timeRange, setTimeRange] = useState('1h')
  const { refreshInterval } = useAppContext()

  // Fetch current system metrics
  const {
    data: systemData,
    loading: systemLoading,
    error: systemError,
    refetch: refetchSystem,
  } = useFetchStats(() => fetchSystemMetrics(), { staleTime: 3000 })

  // Fetch GPU metrics
  const {
    data: gpuData,
    loading: gpuLoading,
    refetch: refetchGPU,
  } = useFetchStats(() => fetchGPUMetrics(), { staleTime: 3000 })

  // Fetch history
  const {
    data: historyData,
    loading: historyLoading,
    error: historyError,
    refetch: refetchHistory,
  } = useFetchStats(
    () => fetchSystemMetricsHistory(timeRange, 100),
    {
      staleTime: 5000,
      deps: [timeRange],
    }
  )

  // Auto-refresh
  useAutoRefresh(
    useCallback(() => {
      refetchSystem()
      refetchGPU()
      refetchHistory()
    }, [refetchSystem, refetchGPU, refetchHistory]),
    refreshInterval
  )

  const loading = systemLoading || historyLoading
  const chartData = historyData?.data || []

  // Scroll to section on mount if specified
  useEffect(() => {
    if (initialSection && !loading) {
      const element = document.getElementById(`chart-${initialSection}`)
      if (element) {
        setTimeout(() => {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 100)
      }
    }
  }, [initialSection, loading])

  if (systemError || historyError) {
    return (
      <ErrorState
        message={systemError?.message || historyError?.message}
        onRetry={() => {
          refetchSystem()
          refetchHistory()
        }}
      />
    )
  }

  // Extract current values
  const cpuPercent = systemData?.cpu_percent ?? 0
  const memoryPercent = systemData?.memory_percent ?? 0
  const memoryUsed = systemData?.memory_used_gb ?? 0
  const memoryTotal = systemData?.memory_total_gb ?? 0
  const gpuAvailable = gpuData?.available ?? false
  const gpuUtil = gpuData?.avg_gpu_utilization_percent ?? 0
  const gpuTemp = gpuData?.avg_temperature_celsius ?? 0
  const vramUsed = gpuData?.used_vram_gb ?? 0
  const vramTotal = gpuData?.total_vram_gb ?? 0

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
            System Metrics
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Real-time system resource monitoring
          </p>
        </div>
        <div className="flex items-center gap-4">
          {/* Time Range Selector */}
          <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
            {Object.entries(SYSTEM_TIME_RANGES).map(([key, config]) => (
              <button
                key={key}
                onClick={() => setTimeRange(key)}
                className={clsx(
                  'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                  timeRange === key
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                )}
              >
                {config.label}
              </button>
            ))}
          </div>
          {/* Refresh Button */}
          <button
            onClick={() => {
              refetchSystem()
              refetchGPU()
              refetchHistory()
            }}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={clsx('w-5 h-5 text-slate-500', loading && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KPICard
          title="CPU"
          value={cpuPercent}
          unit="%"
          subtitle={`${systemData?.cpu_count_logical || 0} cores`}
          color={cpuPercent > 80 ? 'error' : cpuPercent > 50 ? 'warning' : 'success'}
          loading={systemLoading}
        />
        <KPICard
          title="RAM"
          value={memoryUsed}
          unit="GB"
          subtitle={`${memoryPercent.toFixed(0)}% of ${memoryTotal.toFixed(0)}GB`}
          color={memoryPercent > 80 ? 'error' : memoryPercent > 60 ? 'warning' : 'success'}
          loading={systemLoading}
        />
        <KPICard
          title="GPU"
          value={gpuAvailable ? gpuUtil : 'N/A'}
          unit={gpuAvailable ? '%' : ''}
          subtitle={gpuAvailable ? 'Utilization' : 'Not detected'}
          color={gpuAvailable ? (gpuUtil > 80 ? 'error' : 'success') : 'primary'}
          loading={gpuLoading}
        />
        <KPICard
          title="VRAM"
          value={gpuAvailable ? vramUsed : 'N/A'}
          unit={gpuAvailable ? 'GB' : ''}
          subtitle={gpuAvailable ? `of ${vramTotal.toFixed(1)}GB` : 'Not available'}
          color="primary"
          loading={gpuLoading}
        />
        <KPICard
          title="GPU Temp"
          value={gpuAvailable ? gpuTemp : 'N/A'}
          unit={gpuAvailable ? '°C' : ''}
          subtitle={gpuAvailable ? (gpuTemp > 80 ? 'High!' : 'Normal') : 'N/A'}
          color={gpuAvailable ? (gpuTemp > 80 ? 'error' : gpuTemp > 60 ? 'warning' : 'success') : 'primary'}
          loading={gpuLoading}
        />
        <KPICard
          title="Data Points"
          value={chartData.length}
          subtitle={`${timeRange} history`}
          color="primary"
          loading={historyLoading}
        />
      </div>

      {/* CPU & Memory Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MetricChart
          title="CPU Utilization"
          data={chartData}
          dataKey="cpu_percent"
          color={CHART_COLORS.success}
          unit="%"
          icon={Cpu}
          loading={historyLoading}
          yDomain={[0, 100]}
        />
        <MetricChart
          title="Memory Usage"
          data={chartData}
          dataKey="memory_percent"
          color={CHART_COLORS.warning}
          unit="%"
          icon={MemoryStick}
          loading={historyLoading}
          yDomain={[0, 100]}
        />
      </div>

      {/* GPU Charts (if available) */}
      {gpuAvailable && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MetricChart
            title="GPU Utilization"
            data={chartData}
            dataKey="gpu_utilization_percent"
            color={CHART_COLORS.primary}
            unit="%"
            icon={Activity}
            loading={historyLoading}
            yDomain={[0, 100]}
          />
          <MetricChart
            title="VRAM Usage"
            data={chartData}
            dataKey="vram_used_gb"
            color={CHART_COLORS.secondary}
            unit=" GB"
            icon={HardDrive}
            loading={historyLoading}
          />
        </div>
      )}

      {/* GPU Temperature & Queue Depth */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {gpuAvailable && (
          <MetricChart
            title="GPU Temperature"
            data={chartData}
            dataKey="gpu_temperature_celsius"
            color="hsl(0, 84%, 60%)"
            unit="°C"
            icon={Thermometer}
            loading={historyLoading}
          />
        )}
        <MetricChart
          title="Request Queue Depth"
          data={chartData}
          dataKey="queue_depth"
          color={CHART_COLORS.info}
          unit=""
          icon={ListOrdered}
          loading={historyLoading}
        />
      </div>

      {/* GPU Not Available Notice */}
      {!gpuAvailable && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-slate-200 dark:bg-slate-700">
              <Activity className="w-5 h-5 text-slate-500" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-700 dark:text-slate-300">
                GPU Not Detected
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                NVIDIA GPU metrics are not available on this system. GPU charts will appear when running on a system with nvidia-smi.
              </p>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  )
}

export default System
