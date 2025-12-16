/**
 * Loading skeleton components for content placeholders.
 */

import { clsx } from 'clsx'

/**
 * Basic skeleton element with pulse animation.
 */
export function Skeleton({ className, ...props }) {
  return (
    <div
      className={clsx(
        'animate-pulse rounded-md bg-slate-200 dark:bg-slate-700',
        className
      )}
      {...props}
    />
  )
}

/**
 * Skeleton for a stats card.
 */
export function StatsCardSkeleton() {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-10 w-10 rounded-full" />
      </div>
      <Skeleton className="mt-4 h-8 w-32" />
      <Skeleton className="mt-2 h-4 w-20" />
    </div>
  )
}

/**
 * Skeleton for a chart.
 */
export function ChartSkeleton({ height = 300 }) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="h-5 w-32" />
        <div className="flex gap-2">
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-8 w-16" />
        </div>
      </div>
      <Skeleton className="w-full" style={{ height }} />
    </div>
  )
}

/**
 * Skeleton for a table row.
 */
export function TableRowSkeleton({ columns = 5 }) {
  return (
    <tr className="border-b border-slate-200 dark:border-slate-700">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  )
}

/**
 * Skeleton for a table.
 */
export function TableSkeleton({ rows = 5, columns = 5 }) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden">
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-8 w-24" />
        </div>
      </div>
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
            {Array.from({ length: columns }).map((_, i) => (
              <th key={i} className="px-4 py-3 text-left">
                <Skeleton className="h-4 w-20" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <TableRowSkeleton key={i} columns={columns} />
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Full page loading skeleton.
 */
export function PageSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-32" />
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCardSkeleton />
        <StatsCardSkeleton />
        <StatsCardSkeleton />
        <StatsCardSkeleton />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>

      {/* Table */}
      <TableSkeleton />
    </div>
  )
}

export default Skeleton
