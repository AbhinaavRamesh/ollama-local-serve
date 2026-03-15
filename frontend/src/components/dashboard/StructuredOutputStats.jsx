/**
 * Structured Output & Tool Calling statistics card for the dashboard.
 * Shows schema validation rates, tool call frequencies, and per-model breakdown.
 */

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Braces, Wrench, CheckCircle, XCircle } from 'lucide-react'

export function StructuredOutputStats({ refreshInterval = 5000 }) {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${apiUrl}/api/structured/stats`)
      if (res.ok) setStats(await res.json())
    } catch {
      // Silently fail - feature may not be used yet
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, refreshInterval)
    return () => clearInterval(interval)
  }, [fetchData, refreshInterval])

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 animate-pulse">
        <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded w-1/3 mb-4" />
        <div className="h-20 bg-slate-200 dark:bg-slate-700 rounded" />
      </div>
    )
  }

  const totalRequests = stats?.total_requests || 0

  if (totalRequests === 0) {
    return (
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
        <div className="flex items-center gap-2 mb-3">
          <Braces className="w-5 h-5 text-slate-400" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
            Structured Outputs & Tools
          </h3>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No structured output or tool calling requests yet. Use{' '}
          <code className="text-xs bg-slate-100 dark:bg-slate-700 px-1 py-0.5 rounded">
            POST /api/chat/structured
          </code>{' '}
          or{' '}
          <code className="text-xs bg-slate-100 dark:bg-slate-700 px-1 py-0.5 rounded">
            POST /api/chat/tools
          </code>{' '}
          to get started.
        </p>
      </div>
    )
  }

  const so = stats?.structured_outputs || {}
  const tc = stats?.tool_calls || {}
  const byTool = tc.by_tool || {}

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Braces className="w-5 h-5 text-purple-500" />
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
          Structured Outputs & Tools
        </h3>
        <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
          {totalRequests} requests
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Structured Output Stats */}
        {so.total > 0 && (
          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <Braces className="w-4 h-4 text-blue-400" />
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Structured Outputs
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">{so.total}</div>
                <div className="text-xs text-slate-500">Total</div>
              </div>
              <div>
                <div className={`text-2xl font-bold ${so.validation_rate >= 90 ? 'text-emerald-500' : so.validation_rate >= 70 ? 'text-amber-500' : 'text-red-500'}`}>
                  {so.validation_rate}%
                </div>
                <div className="text-xs text-slate-500">Valid</div>
              </div>
            </div>

            {/* Validation bar */}
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div className="flex h-full">
                <div
                  className="bg-emerald-500 transition-all"
                  style={{ width: `${so.validation_rate}%` }}
                />
                <div
                  className="bg-red-400"
                  style={{ width: `${100 - so.validation_rate}%` }}
                />
              </div>
            </div>
            <div className="flex justify-between text-xs mt-1 text-slate-500">
              <span className="flex items-center gap-1">
                <CheckCircle className="w-3 h-3 text-emerald-500" /> {so.valid} valid
              </span>
              <span className="flex items-center gap-1">
                <XCircle className="w-3 h-3 text-red-400" /> {so.invalid} invalid
              </span>
            </div>

            {so.avg_latency_ms > 0 && (
              <div className="mt-2 text-xs text-slate-500">
                Avg latency: <span className="font-medium">{so.avg_latency_ms}ms</span>
              </div>
            )}
          </div>
        )}

        {/* Tool Call Stats */}
        {tc.total > 0 && (
          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <Wrench className="w-4 h-4 text-orange-400" />
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Tool Calls
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">{tc.total}</div>
                <div className="text-xs text-slate-500">Total</div>
              </div>
              <div>
                <div className={`text-2xl font-bold ${tc.success_rate >= 90 ? 'text-emerald-500' : 'text-amber-500'}`}>
                  {tc.success_rate}%
                </div>
                <div className="text-xs text-slate-500">Success</div>
              </div>
            </div>

            {/* Tool breakdown */}
            {Object.keys(byTool).length > 0 && (
              <div className="space-y-1.5">
                {Object.entries(byTool)
                  .sort(([, a], [, b]) => b.total - a.total)
                  .slice(0, 5)
                  .map(([tool, counts]) => (
                    <div key={tool} className="flex items-center gap-2 text-xs">
                      <span className="text-slate-600 dark:text-slate-400 min-w-[90px] truncate font-mono">
                        {tool}
                      </span>
                      <div className="flex-1 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-orange-400 rounded-full"
                          style={{
                            width: `${Math.round((counts.total / tc.total) * 100)}%`,
                          }}
                        />
                      </div>
                      <span className="text-slate-500 min-w-[20px] text-right">{counts.total}</span>
                    </div>
                  ))}
              </div>
            )}

            {tc.avg_latency_ms > 0 && (
              <div className="mt-2 text-xs text-slate-500">
                Avg latency: <span className="font-medium">{tc.avg_latency_ms}ms</span>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default StructuredOutputStats
