/**
 * KPI Card with animated counter and sparkline.
 */

import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import { LineChart, Line, ResponsiveContainer } from 'recharts'
import { formatNumber } from '../../utils/formatters'
import { CHART_COLORS } from '../../utils/constants'

/**
 * Animated counter that ticks up to the target value.
 */
function AnimatedCounter({ value, duration = 1000, format = true }) {
  const [displayValue, setDisplayValue] = useState(0)
  const startTime = useRef(null)
  const startValue = useRef(0)

  useEffect(() => {
    startValue.current = displayValue
    startTime.current = Date.now()

    const animate = () => {
      const now = Date.now()
      const elapsed = now - startTime.current
      const progress = Math.min(elapsed / duration, 1)

      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      const current = startValue.current + (value - startValue.current) * eased

      setDisplayValue(current)

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)
  }, [value, duration])

  return (
    <span>{format ? formatNumber(displayValue) : Math.round(displayValue)}</span>
  )
}

/**
 * Mini sparkline chart for showing trends.
 */
function Sparkline({ data, color = CHART_COLORS.primary }) {
  if (!data || data.length < 2) return null

  const chartData = data.map((value, index) => ({ value, index }))

  return (
    <div className="h-10 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/**
 * KPI Card with glassmorphism design.
 * @param {Object} props
 * @param {string} props.title - Card title
 * @param {number} props.value - Main value
 * @param {string} props.unit - Value unit
 * @param {string} props.subtitle - Additional context
 * @param {Array} props.sparklineData - Array of numbers for sparkline
 * @param {string} props.color - Color theme (primary, success, warning, error)
 * @param {boolean} props.loading - Loading state
 * @param {Function} props.onClick - Click handler
 * @param {string} props.href - Link destination
 */
export function KPICard({
  title,
  value,
  unit,
  subtitle,
  sparklineData,
  color = 'primary',
  loading = false,
  onClick,
  href,
}) {
  const navigate = useNavigate()
  const isClickable = onClick || href
  const colorMap = {
    primary: {
      gradient: 'from-blue-500/10 to-purple-500/10',
      border: 'border-blue-500/20',
      text: 'text-blue-600 dark:text-blue-400',
      chart: CHART_COLORS.primary,
    },
    success: {
      gradient: 'from-emerald-500/10 to-teal-500/10',
      border: 'border-emerald-500/20',
      text: 'text-emerald-600 dark:text-emerald-400',
      chart: CHART_COLORS.success,
    },
    warning: {
      gradient: 'from-amber-500/10 to-orange-500/10',
      border: 'border-amber-500/20',
      text: 'text-amber-600 dark:text-amber-400',
      chart: CHART_COLORS.warning,
    },
    error: {
      gradient: 'from-red-500/10 to-pink-500/10',
      border: 'border-red-500/20',
      text: 'text-red-600 dark:text-red-400',
      chart: CHART_COLORS.error,
    },
  }

  const colors = colorMap[color] || colorMap.primary

  if (loading) {
    return (
      <div
        className={clsx(
          'rounded-xl border backdrop-blur-sm p-6',
          'bg-gradient-to-br from-slate-100/50 to-slate-200/50',
          'dark:from-slate-800/50 dark:to-slate-700/50',
          'border-slate-200/50 dark:border-slate-700/50',
          'animate-pulse'
        )}
      >
        <div className="h-4 w-24 bg-slate-300 dark:bg-slate-600 rounded mb-4" />
        <div className="h-8 w-32 bg-slate-300 dark:bg-slate-600 rounded mb-2" />
        <div className="h-10 w-full bg-slate-300 dark:bg-slate-600 rounded" />
      </div>
    )
  }

  const handleClick = () => {
    if (onClick) onClick()
    if (href) navigate(href.replace('#', ''))
  }

  return (
    <div
      onClick={isClickable ? handleClick : undefined}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => e.key === 'Enter' && handleClick() : undefined}
      className={clsx(
        'rounded-xl border backdrop-blur-sm p-6',
        'bg-gradient-to-br',
        colors.gradient,
        colors.border,
        'transition-all duration-300 hover:shadow-lg',
        isClickable && 'cursor-pointer hover:scale-[1.02] hover:shadow-xl'
      )}
    >
      {/* Title with arrow indicator if clickable */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-slate-600 dark:text-slate-400">
          {title}
        </h3>
        {isClickable && (
          <svg className="w-4 h-4 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        )}
      </div>

      {/* Value with animated counter */}
      <div className="flex items-baseline gap-2 mb-1">
        <span className={clsx('text-3xl font-bold', colors.text)}>
          <AnimatedCounter value={value} />
        </span>
        {unit && (
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {unit}
          </span>
        )}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
          {subtitle}
        </p>
      )}

      {/* Sparkline */}
      {sparklineData && sparklineData.length > 0 && (
        <Sparkline data={sparklineData} color={colors.chart} />
      )}
    </div>
  )
}

export default KPICard
