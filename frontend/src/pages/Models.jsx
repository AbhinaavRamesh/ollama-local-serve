/**
 * Models page - model-specific analytics.
 */

import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Box } from 'lucide-react'
import { ModelComparison } from '../components/tables/ModelComparison'
import { TrendChart } from '../components/charts/TrendChart'
import { KPICard } from '../components/dashboard/KPICard'
import { useFetchStats } from '../hooks/useFetchStats'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { useAppContext } from '../context/AppContext'
import { fetchModels } from '../utils/api'
import { NoModelsState } from '../components/ui/EmptyState'

/**
 * Models page component.
 */
export function Models() {
  const [selectedModel, setSelectedModel] = useState(null)
  const { refreshInterval } = useAppContext()

  // Fetch models
  const {
    data: modelsData,
    loading,
    error,
    refetch,
  } = useFetchStats(() => fetchModels(), {
    staleTime: 30000,
  })

  // Auto-refresh
  useAutoRefresh(refetch, refreshInterval)

  const models = modelsData?.models || []
  const totalModels = modelsData?.total_models || 0

  // Calculate totals
  const totalRequests = models.reduce((sum, m) => sum + m.requests_count, 0)
  const totalTokens = models.reduce((sum, m) => sum + m.tokens_generated, 0)
  const avgLatency = models.length > 0
    ? models.reduce((sum, m) => sum + m.avg_latency_ms, 0) / models.length
    : 0
  const totalErrors = models.reduce((sum, m) => sum + m.error_count, 0)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Models
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Model performance and statistics
          </p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Models"
          value={totalModels}
          subtitle="Available models"
          color="primary"
          loading={loading}
        />
        <KPICard
          title="Total Requests"
          value={totalRequests}
          subtitle="Across all models"
          color="primary"
          loading={loading}
        />
        <KPICard
          title="Total Tokens"
          value={totalTokens}
          subtitle="Generated across all models"
          color="success"
          loading={loading}
        />
        <KPICard
          title="Avg Latency"
          value={avgLatency}
          unit="ms"
          subtitle="Average across models"
          color={avgLatency > 500 ? 'warning' : 'success'}
          loading={loading}
        />
      </div>

      {/* Model Comparison */}
      {models.length === 0 && !loading ? (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
          <NoModelsState />
        </div>
      ) : (
        <ModelComparison
          models={models}
          loading={loading}
        />
      )}

      {/* Model Selector for Detailed View */}
      {models.length > 0 && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
          <div className="mb-4">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-2">
              Model Details
            </h3>
            <div className="flex flex-wrap gap-2">
              {models.map((model) => (
                <button
                  key={model.model_name}
                  onClick={() => setSelectedModel(
                    selectedModel === model.model_name ? null : model.model_name
                  )}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    selectedModel === model.model_name
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                      : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'
                  }`}
                >
                  <Box className="h-4 w-4" />
                  {model.model_name}
                </button>
              ))}
            </div>
          </div>

          {selectedModel && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="pt-4 border-t border-slate-200 dark:border-slate-700"
            >
              {(() => {
                const model = models.find((m) => m.model_name === selectedModel)
                if (!model) return null

                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        Requests
                      </p>
                      <p className="text-2xl font-bold text-slate-900 dark:text-white">
                        {model.requests_count.toLocaleString()}
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        Tokens Generated
                      </p>
                      <p className="text-2xl font-bold text-slate-900 dark:text-white">
                        {model.tokens_generated.toLocaleString()}
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        Avg Latency
                      </p>
                      <p className={`text-2xl font-bold ${
                        model.avg_latency_ms > 1000
                          ? 'text-red-600 dark:text-red-400'
                          : model.avg_latency_ms > 500
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-emerald-600 dark:text-emerald-400'
                      }`}>
                        {model.avg_latency_ms.toFixed(0)}ms
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        Errors
                      </p>
                      <p className={`text-2xl font-bold ${
                        model.error_count > 0
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-emerald-600 dark:text-emerald-400'
                      }`}>
                        {model.error_count}
                      </p>
                    </div>
                  </div>
                )
              })()}
            </motion.div>
          )}
        </div>
      )}
    </motion.div>
  )
}

export default Models
