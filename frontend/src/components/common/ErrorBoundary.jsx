/**
 * Error boundary component for catching React errors.
 */

import { ErrorBoundary as ReactErrorBoundary } from 'react-error-boundary'
import { AlertTriangle, RefreshCw } from 'lucide-react'

/**
 * Fallback component shown when an error occurs.
 */
function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div className="min-h-[400px] flex items-center justify-center p-8">
      <div className="max-w-md w-full text-center">
        <div className="mx-auto w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-6">
          <AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-400" />
        </div>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
          Something went wrong
        </h2>
        <p className="text-slate-600 dark:text-slate-400 mb-4">
          An unexpected error occurred while rendering this page.
        </p>
        {error?.message && (
          <pre className="text-left text-sm bg-slate-100 dark:bg-slate-800 rounded-lg p-4 mb-6 overflow-auto max-h-32">
            <code className="text-red-600 dark:text-red-400">
              {error.message}
            </code>
          </pre>
        )}
        <button
          onClick={resetErrorBoundary}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Try again
        </button>
      </div>
    </div>
  )
}

/**
 * Error boundary wrapper component.
 */
export function ErrorBoundary({ children, onReset }) {
  const handleReset = () => {
    if (onReset) {
      onReset()
    }
  }

  return (
    <ReactErrorBoundary
      FallbackComponent={ErrorFallback}
      onReset={handleReset}
      onError={(error, errorInfo) => {
        console.error('Error caught by boundary:', error, errorInfo)
      }}
    >
      {children}
    </ReactErrorBoundary>
  )
}

export default ErrorBoundary
