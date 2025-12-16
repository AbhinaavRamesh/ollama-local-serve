/**
 * Latency chart showing percentile distribution.
 */

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { CHART_COLORS } from '../../utils/constants'
import { formatDuration } from '../../utils/formatters'
import { ChartSkeleton } from '../ui/LoadingSkeleton'

/**
 * Custom tooltip for latency chart.
 */
function LatencyTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg p-3">
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">
        {typeof label === 'string' && label.includes('T')
          ? format(parseISO(label), 'MMM d, HH:mm')
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
            {formatDuration(entry.value)}
          </span>
        </div>
      ))}
    </div>
  )
}

/**
 * Latency chart with percentile bands.
 * @param {Object} props
 * @param {Array} props.data - Chart data with p50, p95, p99 values
 * @param {boolean} props.loading - Loading state
 * @param {number} props.slaTarget - SLA target in ms (shows reference line)
 */
export function LatencyChart({
  data = [],
  loading = false,
  slaTarget,
  height = 300,
}) {
  if (loading) {
    return <ChartSkeleton height={height} />
  }

  const formatXAxis = (value) => {
    if (!value) return ''
    try {
      const date = typeof value === 'string' ? parseISO(value) : value
      return format(date, 'HH:mm')
    } catch {
      return value
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-base font-semibold text-slate-900 dark:text-white">
            Request Latency
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Percentile distribution over time
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-emerald-500" />
            <span className="text-slate-600 dark:text-slate-400">p50</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-amber-500" />
            <span className="text-slate-600 dark:text-slate-400">p95</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-500" />
            <span className="text-slate-600 dark:text-slate-400">p99</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <defs>
              <linearGradient id="latency-p50" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={CHART_COLORS.success} stopOpacity={0.3} />
                <stop offset="95%" stopColor={CHART_COLORS.success} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="latency-p95" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={CHART_COLORS.warning} stopOpacity={0.3} />
                <stop offset="95%" stopColor={CHART_COLORS.warning} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="latency-p99" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={CHART_COLORS.error} stopOpacity={0.3} />
                <stop offset="95%" stopColor={CHART_COLORS.error} stopOpacity={0} />
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
              tick={{ fontSize: 12 }}
              stroke="currentColor"
              className="text-slate-400"
            />
            <YAxis
              tickFormatter={(value) => formatDuration(value)}
              tick={{ fontSize: 12 }}
              stroke="currentColor"
              className="text-slate-400"
              width={60}
            />
            <Tooltip content={<LatencyTooltip />} />

            {/* SLA reference line */}
            {slaTarget && (
              <ReferenceLine
                y={slaTarget}
                stroke={CHART_COLORS.muted}
                strokeDasharray="5 5"
                label={{
                  value: `SLA: ${formatDuration(slaTarget)}`,
                  position: 'right',
                  fill: CHART_COLORS.muted,
                  fontSize: 11,
                }}
              />
            )}

            {/* Stack areas from p99 (highest) to p50 (lowest) */}
            <Area
              type="monotone"
              dataKey="p99"
              name="p99"
              stroke={CHART_COLORS.error}
              strokeWidth={2}
              fill="url(#latency-p99)"
            />
            <Area
              type="monotone"
              dataKey="p95"
              name="p95"
              stroke={CHART_COLORS.warning}
              strokeWidth={2}
              fill="url(#latency-p95)"
            />
            <Area
              type="monotone"
              dataKey="p50"
              name="p50"
              stroke={CHART_COLORS.success}
              strokeWidth={2}
              fill="url(#latency-p50)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default LatencyChart
