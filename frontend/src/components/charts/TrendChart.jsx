/**
 * Trend chart component with time range selection.
 */

import { useState } from 'react'
import { clsx } from 'clsx'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { Download } from 'lucide-react'
import { TIME_RANGES, CHART_COLORS } from '../../utils/constants'
import { formatNumber } from '../../utils/formatters'
import { ChartSkeleton } from '../ui/LoadingSkeleton'

/**
 * Custom tooltip for charts.
 */
function CustomTooltip({ active, payload, label }) {
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
            {formatNumber(entry.value)}
          </span>
        </div>
      ))}
    </div>
  )
}

/**
 * Time range selector buttons.
 */
function TimeRangeSelector({ value, onChange, options = TIME_RANGES }) {
  return (
    <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
      {Object.entries(options).map(([key, config]) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={clsx(
            'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
            value === key
              ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          )}
        >
          {config.label}
        </button>
      ))}
    </div>
  )
}

/**
 * Trend chart with gradient fill.
 * @param {Object} props
 * @param {Array} props.data - Chart data
 * @param {string} props.title - Chart title
 * @param {string} props.xKey - Key for X axis
 * @param {string} props.yKey - Key for Y axis
 * @param {string} props.timeRange - Current time range
 * @param {Function} props.onTimeRangeChange - Time range change handler
 * @param {boolean} props.loading - Loading state
 * @param {string} props.color - Chart color
 * @param {boolean} props.showGradient - Show gradient fill
 */
export function TrendChart({
  data = [],
  title,
  xKey = 'timestamp',
  yKey = 'value',
  yLabel,
  timeRange = '1h',
  onTimeRangeChange,
  loading = false,
  color = CHART_COLORS.primary,
  showGradient = true,
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

  const gradientId = `gradient-${title?.replace(/\s/g, '-') || 'chart'}`

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-base font-semibold text-slate-900 dark:text-white">
            {title}
          </h3>
          {yLabel && (
            <p className="text-sm text-slate-500 dark:text-slate-400">{yLabel}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onTimeRangeChange && (
            <TimeRangeSelector
              value={timeRange}
              onChange={onTimeRangeChange}
            />
          )}
        </div>
      </div>

      {/* Chart */}
      <div style={{ height }}>
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
              dataKey={xKey}
              tickFormatter={formatXAxis}
              tick={{ fontSize: 12 }}
              stroke="currentColor"
              className="text-slate-400"
            />
            <YAxis
              tickFormatter={(value) => formatNumber(value)}
              tick={{ fontSize: 12 }}
              stroke="currentColor"
              className="text-slate-400"
              width={50}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey={yKey}
              name={yLabel || yKey}
              stroke={color}
              strokeWidth={2}
              fill={showGradient ? `url(#${gradientId})` : 'transparent'}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default TrendChart
