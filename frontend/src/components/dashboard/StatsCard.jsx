/**
 * Stats card component for displaying KPI metrics.
 */

import { clsx } from 'clsx'
import { TrendingUp, TrendingDown } from 'lucide-react'
import * as Icons from 'lucide-react'
import { Skeleton } from '../ui/LoadingSkeleton'
import { formatNumber } from '../../utils/formatters'

/**
 * Stats card for displaying a single metric.
 * @param {Object} props
 * @param {string} props.title - Card title
 * @param {number|string} props.value - Main value to display
 * @param {string} props.unit - Unit label (e.g., "ms", "tokens")
 * @param {string} props.icon - Icon name from lucide-react
 * @param {number} props.trend - Trend percentage (positive or negative)
 * @param {string} props.trendLabel - Label for trend (e.g., "vs last hour")
 * @param {boolean} props.loading - Loading state
 * @param {string} props.className - Additional CSS classes
 */
export function StatsCard({
  title,
  value,
  unit,
  icon,
  trend,
  trendLabel,
  loading = false,
  className,
}) {
  const Icon = icon ? Icons[icon] : null
  const hasTrend = trend !== undefined && trend !== null

  if (loading) {
    return (
      <div
        className={clsx(
          'rounded-xl border border-slate-200 dark:border-slate-700',
          'bg-white dark:bg-slate-800 p-6',
          'transition-all duration-300',
          className
        )}
      >
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-10 w-10 rounded-lg" />
        </div>
        <Skeleton className="h-9 w-32 mb-2" />
        <Skeleton className="h-4 w-20" />
      </div>
    )
  }

  return (
    <div
      className={clsx(
        'rounded-xl border border-slate-200 dark:border-slate-700',
        'bg-white dark:bg-slate-800 p-6',
        'hover:shadow-lg hover:border-slate-300 dark:hover:border-slate-600',
        'transition-all duration-300',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400">
          {title}
        </h3>
        {Icon && (
          <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/30">
            <Icon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
        )}
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold text-slate-900 dark:text-white">
          {typeof value === 'number' ? formatNumber(value) : value}
        </span>
        {unit && (
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {unit}
          </span>
        )}
      </div>

      {/* Trend */}
      {hasTrend && (
        <div className="flex items-center gap-1.5 mt-2">
          {trend >= 0 ? (
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          ) : (
            <TrendingDown className="h-4 w-4 text-red-500" />
          )}
          <span
            className={clsx(
              'text-sm font-medium',
              trend >= 0
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-red-600 dark:text-red-400'
            )}
          >
            {trend >= 0 ? '+' : ''}
            {trend.toFixed(1)}%
          </span>
          {trendLabel && (
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {trendLabel}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Grid container for stats cards.
 */
export function StatsCardGrid({ children }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {children}
    </div>
  )
}

export default StatsCard
