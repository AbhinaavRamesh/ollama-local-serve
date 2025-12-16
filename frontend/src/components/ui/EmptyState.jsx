/**
 * Empty state component for when there's no data.
 */

import { clsx } from 'clsx'
import * as Icons from 'lucide-react'

/**
 * Empty state display component.
 * @param {Object} props
 * @param {string} props.icon - Icon name from lucide-react
 * @param {string} props.title - Title text
 * @param {string} props.description - Description text
 * @param {React.ReactNode} props.action - Optional action button
 * @param {string} props.className - Additional CSS classes
 */
export function EmptyState({
  icon = 'Inbox',
  title = 'No data',
  description = 'There is no data to display.',
  action,
  className,
}) {
  const Icon = Icons[icon] || Icons.Inbox

  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center py-12 px-4 text-center',
        className
      )}
    >
      <div className="rounded-full bg-slate-100 dark:bg-slate-800 p-4 mb-4">
        <Icon className="h-8 w-8 text-slate-400 dark:text-slate-500" />
      </div>
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">
        {title}
      </h3>
      <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mb-4">
        {description}
      </p>
      {action && <div>{action}</div>}
    </div>
  )
}

/**
 * Empty state for no search results.
 */
export function NoResultsState({ searchTerm, onClear }) {
  return (
    <EmptyState
      icon="Search"
      title="No results found"
      description={`No results match "${searchTerm}". Try adjusting your search or filters.`}
      action={
        onClear && (
          <button
            onClick={onClear}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Clear search
          </button>
        )
      }
    />
  )
}

/**
 * Empty state for errors.
 */
export function ErrorState({ message, onRetry }) {
  return (
    <EmptyState
      icon="AlertTriangle"
      title="Something went wrong"
      description={message || 'An error occurred while loading data.'}
      action={
        onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <Icons.RefreshCw className="h-4 w-4" />
            Try again
          </button>
        )
      }
    />
  )
}

/**
 * Empty state for no logs.
 */
export function NoLogsState() {
  return (
    <EmptyState
      icon="ScrollText"
      title="No logs yet"
      description="Request logs will appear here once you start making requests to the Ollama service."
    />
  )
}

/**
 * Empty state for no models.
 */
export function NoModelsState() {
  return (
    <EmptyState
      icon="Box"
      title="No models available"
      description="No models have been loaded yet. Pull a model using the Ollama CLI to get started."
    />
  )
}

export default EmptyState
