/**
 * Smart Model Router status card for the dashboard.
 * Shows active routing rules, model availability, and recent routing decisions.
 */

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { GitBranch, Target, ArrowRight, RefreshCw } from 'lucide-react'

export function RouterStatus({ refreshInterval = 5000 }) {
  const [config, setConfig] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || ''
      const [configRes, statsRes] = await Promise.all([
        fetch(`${apiUrl}/api/router/config`),
        fetch(`${apiUrl}/api/router/stats`),
      ])

      if (configRes.ok) setConfig(await configRes.json())
      if (statsRes.ok) setStats(await statsRes.json())
      setError(null)
    } catch (err) {
      setError(err.message)
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

  if (!config?.enabled) {
    return (
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
        <div className="flex items-center gap-2 mb-3">
          <GitBranch className="w-5 h-5 text-slate-400" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Smart Router</h3>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Router is disabled. Set <code className="text-xs bg-slate-100 dark:bg-slate-700 px-1 py-0.5 rounded">ROUTER_ENABLED=true</code> to enable.
        </p>
      </div>
    )
  }

  const totalDecisions = stats?.total_decisions || 0
  const byModel = stats?.by_model || {}
  const byTaskType = stats?.by_task_type || {}
  const fallbackRate = stats?.fallback_rate || 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Smart Router</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
            Active
          </span>
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-400">
          Strategy: <span className="font-medium">{config.strategy}</span>
        </div>
      </div>

      {/* Routing Rules */}
      <div className="mb-4">
        <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Routing Rules</h4>
        <div className="space-y-2">
          {(config.rules || []).map((rule, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 text-sm bg-slate-50 dark:bg-slate-900/50 rounded-lg px-3 py-2"
            >
              <Target className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
              <span className="font-medium text-slate-700 dark:text-slate-300 min-w-[80px]">
                {rule.task_type}
              </span>
              <ArrowRight className="w-3 h-3 text-slate-400" />
              <span className="text-slate-600 dark:text-slate-400 truncate">
                {rule.models?.join(', ')}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      {totalDecisions > 0 && (
        <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
          <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">Routing Stats</h4>
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center">
              <div className="text-xl font-bold text-slate-900 dark:text-white">{totalDecisions}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Decisions</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-slate-900 dark:text-white">
                {Object.keys(byModel).length}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Models Used</div>
            </div>
            <div className="text-center">
              <div className={`text-xl font-bold ${fallbackRate > 20 ? 'text-amber-500' : 'text-emerald-500'}`}>
                {fallbackRate}%
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Fallback Rate</div>
            </div>
          </div>

          {/* Model distribution */}
          {Object.keys(byModel).length > 0 && (
            <div className="mt-3 space-y-1.5">
              {Object.entries(byModel)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 5)
                .map(([model, count]) => {
                  const pct = Math.round((count / totalDecisions) * 100)
                  return (
                    <div key={model} className="flex items-center gap-2 text-xs">
                      <span className="text-slate-600 dark:text-slate-400 min-w-[120px] truncate">
                        {model}
                      </span>
                      <div className="flex-1 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-slate-500 dark:text-slate-400 min-w-[35px] text-right">
                        {pct}%
                      </span>
                    </div>
                  )
                })}
            </div>
          )}
        </div>
      )}
    </motion.div>
  )
}

export default RouterStatus
