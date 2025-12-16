/**
 * Model comparison table with stats and charts.
 */

import { useMemo } from 'clsx'
import { clsx } from 'clsx'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { formatNumber, formatDuration, formatTimestamp } from '../../utils/formatters'
import { CHART_COLORS } from '../../utils/constants'
import { TableSkeleton } from '../ui/LoadingSkeleton'
import { NoModelsState } from '../ui/EmptyState'

/**
 * Model comparison component.
 * @param {Object} props
 * @param {Array} props.models - Model statistics
 * @param {boolean} props.loading - Loading state
 */
export function ModelComparison({ models = [], loading = false }) {
  // Sort models by request count
  const sortedModels = [...models].sort(
    (a, b) => b.requests_count - a.requests_count
  )

  // Prepare chart data
  const chartData = sortedModels.slice(0, 10).map((model) => ({
    name: model.model_name,
    requests: model.requests_count,
    latency: model.avg_latency_ms,
    tokens: model.tokens_generated,
  }))

  if (loading) {
    return <TableSkeleton rows={5} columns={5} />
  }

  if (models.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
        <NoModelsState />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats Table */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-base font-semibold text-slate-900 dark:text-white">
            Model Performance
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Statistics per model
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Model
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Requests
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Tokens
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Avg Latency
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Errors
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Last Used
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedModels.map((model, index) => {
                const latencyColor =
                  model.avg_latency_ms > 1000
                    ? 'text-red-600 dark:text-red-400'
                    : model.avg_latency_ms > 500
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-emerald-600 dark:text-emerald-400'

                return (
                  <tr
                    key={model.model_name}
                    className={clsx(
                      'border-b border-slate-200 dark:border-slate-700',
                      'hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors'
                    )}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-900 dark:text-white">
                          {model.model_name}
                        </span>
                        {index === 0 && (
                          <span className="px-1.5 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded">
                            Top
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-sm text-slate-600 dark:text-slate-400">
                        {formatNumber(model.requests_count, 0, false)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-sm text-slate-600 dark:text-slate-400">
                        {formatNumber(model.tokens_generated)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={clsx('text-sm font-medium', latencyColor)}>
                        {formatDuration(model.avg_latency_ms)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className={clsx(
                          'text-sm',
                          model.error_count > 0
                            ? 'text-red-600 dark:text-red-400 font-medium'
                            : 'text-slate-600 dark:text-slate-400'
                        )}
                      >
                        {model.error_count}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-sm text-slate-500 dark:text-slate-400">
                        {model.last_used
                          ? formatTimestamp(model.last_used, 'MMM d, HH:mm')
                          : '-'}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Request Distribution Chart */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
        <div className="mb-6">
          <h3 className="text-base font-semibold text-slate-900 dark:text-white">
            Request Distribution
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Requests per model (top 10)
          </p>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 80 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="currentColor"
                className="text-slate-200 dark:text-slate-700"
              />
              <XAxis
                type="number"
                tickFormatter={(value) => formatNumber(value, 0)}
                tick={{ fontSize: 12 }}
                stroke="currentColor"
                className="text-slate-400"
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 12 }}
                stroke="currentColor"
                className="text-slate-400"
                width={75}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  const data = payload[0].payload
                  return (
                    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg p-3">
                      <p className="text-sm font-medium text-slate-900 dark:text-white mb-1">
                        {data.name}
                      </p>
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        Requests: {formatNumber(data.requests, 0, false)}
                      </p>
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        Avg Latency: {formatDuration(data.latency)}
                      </p>
                    </div>
                  )
                }}
              />
              <Bar dataKey="requests" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      index === 0
                        ? CHART_COLORS.primary
                        : `hsl(221, 83%, ${53 + index * 5}%)`
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

export default ModelComparison
