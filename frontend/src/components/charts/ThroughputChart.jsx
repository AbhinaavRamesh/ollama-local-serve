/**
 * Throughput chart with dual Y-axis (requests + tokens/sec).
 */

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { CHART_COLORS } from '../../utils/constants'
import { formatNumber } from '../../utils/formatters'
import { ChartSkeleton } from '../ui/LoadingSkeleton'

/**
 * Custom tooltip for throughput chart.
 */
function ThroughputTooltip({ active, payload, label }) {
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
            className="w-3 h-3 rounded"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-sm text-slate-600 dark:text-slate-300">
            {entry.name}:
          </span>
          <span className="text-sm font-medium text-slate-900 dark:text-white">
            {formatNumber(entry.value)}
            {entry.name.includes('Tokens') ? '/s' : ''}
          </span>
        </div>
      ))}
    </div>
  )
}

/**
 * Throughput chart with bars for requests and line for tokens/sec.
 * @param {Object} props
 * @param {Array} props.data - Chart data
 * @param {boolean} props.loading - Loading state
 */
export function ThroughputChart({
  data = [],
  loading = false,
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
            Throughput
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Requests and tokens per second
          </p>
        </div>
      </div>

      {/* Chart */}
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
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
              yAxisId="left"
              tickFormatter={(value) => formatNumber(value, 0)}
              tick={{ fontSize: 12 }}
              stroke="currentColor"
              className="text-slate-400"
              width={50}
              label={{
                value: 'Requests',
                angle: -90,
                position: 'insideLeft',
                style: { textAnchor: 'middle', fill: CHART_COLORS.primary },
              }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tickFormatter={(value) => formatNumber(value, 0)}
              tick={{ fontSize: 12 }}
              stroke="currentColor"
              className="text-slate-400"
              width={50}
              label={{
                value: 'Tokens/s',
                angle: 90,
                position: 'insideRight',
                style: { textAnchor: 'middle', fill: CHART_COLORS.secondary },
              }}
            />
            <Tooltip content={<ThroughputTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: '10px' }}
              formatter={(value) => (
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  {value}
                </span>
              )}
            />
            <Bar
              yAxisId="left"
              dataKey="requests"
              name="Requests"
              fill={CHART_COLORS.primary}
              radius={[4, 4, 0, 0]}
              opacity={0.8}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="tokensPerSec"
              name="Tokens/s"
              stroke={CHART_COLORS.secondary}
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default ThroughputChart
