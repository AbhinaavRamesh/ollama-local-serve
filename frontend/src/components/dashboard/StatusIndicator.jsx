/**
 * Status indicator component with animated dot.
 */

import { clsx } from 'clsx'
import { STATUS_COLORS } from '../../utils/constants'

/**
 * Status indicator with colored dot.
 * @param {Object} props
 * @param {string} props.status - Status type (success, error, warning, info, pending)
 * @param {string} props.label - Status label text
 * @param {boolean} props.pulse - Whether to show pulse animation
 * @param {string} props.size - Size variant (sm, md, lg)
 */
export function StatusIndicator({
  status = 'pending',
  label,
  pulse = false,
  size = 'md',
}) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.pending

  const sizeClasses = {
    sm: 'h-2 w-2',
    md: 'h-2.5 w-2.5',
    lg: 'h-3 w-3',
  }

  const textSizes = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  }

  return (
    <div className="flex items-center gap-2">
      <span className="relative flex">
        {pulse && (
          <span
            className={clsx(
              'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
              colors.dot
            )}
          />
        )}
        <span
          className={clsx(
            'relative inline-flex rounded-full',
            sizeClasses[size],
            colors.dot
          )}
        />
      </span>
      {label && (
        <span
          className={clsx(
            'font-medium',
            textSizes[size],
            colors.text
          )}
        >
          {label}
        </span>
      )}
    </div>
  )
}

/**
 * Inline status badge.
 */
export function StatusBadge({ status = 'pending', children }) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.pending

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
        colors.bg,
        colors.text,
        colors.border,
        'border'
      )}
    >
      <span className={clsx('h-1.5 w-1.5 rounded-full', colors.dot)} />
      {children}
    </span>
  )
}

export default StatusIndicator
