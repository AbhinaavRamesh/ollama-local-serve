/**
 * Settings page - configuration and preferences.
 */

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Sun, Moon, RefreshCw, Bell, Download, Bot, Trash2,
  Search, Loader2, Check, AlertCircle, ChevronDown, ChevronUp,
  Star, Settings2, BarChart3, Clock, Zap, Database, FileText, AlertTriangle
} from 'lucide-react'
import { clsx } from 'clsx'
import { useThemeContext } from '../context/ThemeContext'
import { useAppContext } from '../context/AppContext'
import { showSuccess, showError } from '../components/ui/Toast'
import { DEFAULT_REFRESH_INTERVAL } from '../utils/constants'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

/**
 * Settings section component.
 */
function SettingsSection({ title, description, children }) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-slate-900 dark:text-white">
          {title}
        </h3>
        {description && (
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {description}
          </p>
        )}
      </div>
      {children}
    </div>
  )
}

/**
 * Settings option component.
 */
function SettingsOption({ icon: Icon, label, description, children }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-200 dark:border-slate-700 last:border-0">
      <div className="flex items-center gap-3">
        {Icon && (
          <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-700">
            <Icon className="h-4 w-4 text-slate-600 dark:text-slate-400" />
          </div>
        )}
        <div>
          <p className="text-sm font-medium text-slate-900 dark:text-white">
            {label}
          </p>
          {description && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {description}
            </p>
          )}
        </div>
      </div>
      <div>{children}</div>
    </div>
  )
}

/**
 * Model Management Section Component - Enhanced with Repository Integration
 */
function ModelManagementSection() {
  const [ollamaModels, setOllamaModels] = useState([])
  const [repositoryModels, setRepositoryModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [repoLoading, setRepoLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [pulling, setPulling] = useState(null)
  const [pullProgress, setPullProgress] = useState({})
  const [deleting, setDeleting] = useState(null)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('installed')

  // Fetch installed models from Ollama
  const fetchOllamaModels = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/ollama/models`)
      if (response.ok) {
        const data = await response.json()
        setOllamaModels(data.models || [])
      }
    } catch (err) {
      console.error('Failed to fetch ollama models:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch model repository for metadata and favorites
  const fetchRepository = useCallback(async () => {
    setRepoLoading(true)
    try {
      const response = await fetch(`${API_BASE}/models/repository`)
      if (response.ok) {
        const data = await response.json()
        setRepositoryModels(data.models || [])
      }
    } catch (err) {
      console.error('Failed to fetch repository:', err)
    } finally {
      setRepoLoading(false)
    }
  }, [])

  // Sync installed models with repository
  const syncModels = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/models/repository/sync`, { method: 'POST' })
      await fetchRepository()
    } catch (err) {
      console.error('Failed to sync models:', err)
    }
  }, [fetchRepository])

  useEffect(() => {
    fetchOllamaModels()
    fetchRepository()
  }, [fetchOllamaModels, fetchRepository])

  const handleSearch = (query) => {
    setSearchQuery(query)
  }

  // Toggle favorite
  const toggleFavorite = async (modelName, isFavorite) => {
    try {
      const response = await fetch(`${API_BASE}/models/repository/${encodeURIComponent(modelName)}/favorite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_favorite: !isFavorite }),
      })
      if (response.ok) {
        fetchRepository()
        showSuccess(isFavorite ? 'Removed from favorites' : 'Added to favorites')
      }
    } catch (err) {
      showError('Failed to update favorite')
    }
  }

  // Set default model
  const setDefaultModel = async (modelName) => {
    try {
      const response = await fetch(`${API_BASE}/models/repository/${encodeURIComponent(modelName)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_default: true }),
      })
      if (response.ok) {
        fetchRepository()
        showSuccess(`${modelName} set as default`)
      }
    } catch (err) {
      showError('Failed to set default')
    }
  }

  const pullModel = async (modelName) => {
    setPulling(modelName)
    setPullProgress({ [modelName]: { status: 'starting', percent: 0 } })
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/ollama/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: modelName }),
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.error) {
                setError(data.error)
                showError(data.error)
                setPulling(null)
                return
              }
              if (data.status) {
                let percent = 0
                if (data.completed && data.total) {
                  percent = Math.round((data.completed / data.total) * 100)
                }
                setPullProgress({
                  [modelName]: { status: data.status, percent }
                })
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }

      showSuccess(`Model ${modelName} pulled successfully`)
      fetchOllamaModels()
      syncModels()
    } catch (err) {
      setError(err.message)
      showError(err.message)
    } finally {
      setPulling(null)
      setPullProgress({})
    }
  }

  const deleteModel = async (modelName) => {
    if (!confirm(`Are you sure you want to delete ${modelName}?`)) return

    setDeleting(modelName)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/ollama/models/${encodeURIComponent(modelName)}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('Failed to delete model')
      }

      showSuccess(`Model ${modelName} deleted`)
      fetchOllamaModels()
      syncModels()
    } catch (err) {
      setError(err.message)
      showError(err.message)
    } finally {
      setDeleting(null)
    }
  }

  // Get repository info for a model
  const getRepoInfo = (modelName) => {
    const baseName = modelName.split(':')[0]
    return repositoryModels.find(m => m.model_name === baseName || m.model_name === modelName)
  }

  // Filter models based on search
  const filteredOllamaModels = ollamaModels.filter(m =>
    m.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredRepoModels = repositoryModels.filter(m =>
    m.model_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (m.display_name && m.display_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (m.category && m.category.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const favoriteModels = filteredRepoModels.filter(m => m.is_favorite)
  const availableModels = filteredRepoModels.filter(m => !m.is_installed)

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder="Search models..."
          className="w-full pl-10 pr-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-slate-100 dark:bg-slate-700/50 rounded-lg">
        {[
          { id: 'installed', label: 'Installed', count: ollamaModels.length },
          { id: 'favorites', label: 'Favorites', count: favoriteModels.length },
          { id: 'library', label: 'Library', count: repositoryModels.length },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors',
              activeTab === tab.id
                ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            )}
          >
            {tab.label}
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-500 text-slate-600 dark:text-slate-200">
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Tab Content */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {activeTab === 'installed' && (
          <>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-500">Installed on Ollama</span>
              <button
                onClick={() => { fetchOllamaModels(); syncModels(); }}
                className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
                title="Refresh and sync"
              >
                <RefreshCw className={clsx('w-4 h-4 text-slate-500', loading && 'animate-spin')} />
              </button>
            </div>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
              </div>
            ) : filteredOllamaModels.length === 0 ? (
              <p className="text-sm text-slate-500 py-8 text-center">No models installed</p>
            ) : (
              filteredOllamaModels.map((model) => {
                const repoInfo = getRepoInfo(model.name)
                return (
                  <div
                    key={model.name}
                    className={clsx(
                      'flex items-center justify-between p-3 rounded-lg transition-colors',
                      repoInfo?.is_default
                        ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                        : 'bg-slate-50 dark:bg-slate-700/50'
                    )}
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <Bot className="w-5 h-5 text-blue-600 flex-shrink-0" />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-slate-900 dark:text-white text-sm truncate">{model.name}</p>
                          {repoInfo?.is_default && (
                            <span className="text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300 rounded">Default</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                          <span>{model.size ? `${(model.size / 1e9).toFixed(1)} GB` : ''}</span>
                          {repoInfo?.usage_count > 0 && (
                            <>
                              <span>•</span>
                              <span className="flex items-center gap-1">
                                <BarChart3 className="w-3 h-3" />
                                {repoInfo.usage_count} uses
                              </span>
                            </>
                          )}
                          {repoInfo?.total_tokens_generated > 0 && (
                            <>
                              <span>•</span>
                              <span className="flex items-center gap-1">
                                <Zap className="w-3 h-3" />
                                {(repoInfo.total_tokens_generated / 1000).toFixed(1)}k tokens
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        onClick={() => toggleFavorite(model.name.split(':')[0], repoInfo?.is_favorite)}
                        className={clsx(
                          'p-2 rounded-lg transition-colors',
                          repoInfo?.is_favorite
                            ? 'text-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-900/30'
                            : 'text-slate-400 hover:text-yellow-500 hover:bg-slate-100 dark:hover:bg-slate-700'
                        )}
                        title={repoInfo?.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                      >
                        <Star className={clsx('w-4 h-4', repoInfo?.is_favorite && 'fill-current')} />
                      </button>
                      {!repoInfo?.is_default && (
                        <button
                          onClick={() => setDefaultModel(model.name.split(':')[0])}
                          className="p-2 text-slate-400 hover:text-blue-500 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                          title="Set as default"
                        >
                          <Settings2 className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => deleteModel(model.name)}
                        disabled={deleting === model.name}
                        className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50"
                        title="Delete model"
                      >
                        {deleting === model.name ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </>
        )}

        {activeTab === 'favorites' && (
          <>
            {favoriteModels.length === 0 ? (
              <div className="text-center py-8">
                <Star className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No favorite models yet</p>
                <p className="text-xs text-slate-400 mt-1">Star a model to add it here</p>
              </div>
            ) : (
              favoriteModels.map((model) => (
                <div
                  key={model.model_name}
                  className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <Star className="w-5 h-5 text-yellow-500 fill-current flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="font-medium text-slate-900 dark:text-white text-sm">{model.display_name || model.model_name}</p>
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <span className="px-1.5 py-0.5 bg-slate-200 dark:bg-slate-600 rounded">{model.category}</span>
                        {model.size_label && <span>{model.size_label}</span>}
                        {model.is_installed && (
                          <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                            <Check className="w-3 h-3" /> Installed
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => toggleFavorite(model.model_name, true)}
                    className="p-2 text-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-900/30 rounded-lg transition-colors"
                    title="Remove from favorites"
                  >
                    <Star className="w-4 h-4 fill-current" />
                  </button>
                </div>
              ))
            )}
          </>
        )}

        {activeTab === 'library' && (
          <>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-500">Available models in repository</span>
              <button
                onClick={fetchRepository}
                className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
                title="Refresh"
              >
                <RefreshCw className={clsx('w-4 h-4 text-slate-500', repoLoading && 'animate-spin')} />
              </button>
            </div>
            {repoLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
              </div>
            ) : (
              filteredRepoModels.map((model) => {
                const isPulling = pulling === model.model_name
                const progress = pullProgress[model.model_name]

                return (
                  <div
                    key={model.model_name}
                    className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <Bot className={clsx(
                        'w-5 h-5 flex-shrink-0',
                        model.is_installed ? 'text-emerald-600' : 'text-slate-400'
                      )} />
                      <div className="min-w-0">
                        <p className="font-medium text-slate-900 dark:text-white text-sm">{model.display_name || model.model_name}</p>
                        <p className="text-xs text-slate-500 truncate">{model.description}</p>
                        <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                          <span className="px-1.5 py-0.5 bg-slate-200 dark:bg-slate-600 rounded">{model.category}</span>
                          {model.size_label && <span>{model.size_label}</span>}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                      <button
                        onClick={() => toggleFavorite(model.model_name, model.is_favorite)}
                        className={clsx(
                          'p-2 rounded-lg transition-colors',
                          model.is_favorite
                            ? 'text-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-900/30'
                            : 'text-slate-400 hover:text-yellow-500 hover:bg-slate-100 dark:hover:bg-slate-700'
                        )}
                        title={model.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                      >
                        <Star className={clsx('w-4 h-4', model.is_favorite && 'fill-current')} />
                      </button>
                      {model.is_installed ? (
                        <span className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 px-2 py-1 bg-emerald-50 dark:bg-emerald-900/30 rounded-full">
                          <Check className="w-3 h-3" />
                          Installed
                        </span>
                      ) : isPulling ? (
                        <div className="flex items-center gap-2">
                          <div className="text-xs text-slate-500 max-w-[60px] truncate">
                            {progress?.status || 'Starting...'}
                          </div>
                          <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                        </div>
                      ) : (
                        <button
                          onClick={() => pullModel(model.model_name)}
                          disabled={pulling !== null}
                          className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
                        >
                          <Download className="w-3 h-3" />
                          Pull
                        </button>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </>
        )}
      </div>
    </div>
  )
}

/**
 * Data Management Section Component - Clear metrics, logs, and reset data
 */
function DataManagementSection() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [clearing, setClearing] = useState(null)
  const [confirmClear, setConfirmClear] = useState(null)

  const fetchSummary = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/data/summary`)
      if (response.ok) {
        const data = await response.json()
        setSummary(data)
      }
    } catch (err) {
      console.error('Failed to fetch data summary:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSummary()
  }, [fetchSummary])

  const clearData = async (type) => {
    if (confirmClear !== type) {
      setConfirmClear(type)
      return
    }

    setClearing(type)
    setConfirmClear(null)

    try {
      const endpoints = {
        metrics: '/data/metrics',
        logs: '/data/logs',
        all: '/data/all',
      }

      const response = await fetch(`${API_BASE}${endpoints[type]}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        showSuccess(`${type === 'all' ? 'All data' : type.charAt(0).toUpperCase() + type.slice(1)} cleared successfully`)
        fetchSummary()
      } else {
        throw new Error('Failed to clear data')
      }
    } catch (err) {
      showError(err.message)
    } finally {
      setClearing(null)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A'
    return new Date(dateStr).toLocaleString()
  }

  return (
    <div className="space-y-4">
      {/* Data Summary */}
      <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
            <Database className="w-4 h-4" />
            Database Summary
          </h4>
          <button
            onClick={fetchSummary}
            className="p-1 hover:bg-slate-200 dark:hover:bg-slate-600 rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw className={clsx('w-4 h-4 text-slate-500', loading && 'animate-spin')} />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
          </div>
        ) : summary ? (
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-slate-500 dark:text-slate-400">Metrics</p>
              <p className="font-medium text-slate-900 dark:text-white">{summary.metrics_count?.toLocaleString() || 0}</p>
            </div>
            <div>
              <p className="text-slate-500 dark:text-slate-400">Request Logs</p>
              <p className="font-medium text-slate-900 dark:text-white">{summary.logs_count?.toLocaleString() || 0}</p>
            </div>
            <div>
              <p className="text-slate-500 dark:text-slate-400">Oldest Record</p>
              <p className="font-medium text-slate-900 dark:text-white text-xs">{formatDate(summary.oldest_metric)}</p>
            </div>
            <div>
              <p className="text-slate-500 dark:text-slate-400">Newest Record</p>
              <p className="font-medium text-slate-900 dark:text-white text-xs">{formatDate(summary.newest_metric)}</p>
            </div>
            <div className="col-span-2">
              <p className="text-slate-500 dark:text-slate-400">Databases</p>
              <div className="flex gap-2 mt-1">
                {summary.databases?.map((db) => (
                  <span key={db} className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-xs rounded-full">
                    {db}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">No data available</p>
        )}
      </div>

      {/* Clear Actions */}
      <div className="space-y-3">
        {/* Clear Metrics */}
        <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <div className="flex items-center gap-3">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            <div>
              <p className="font-medium text-slate-900 dark:text-white text-sm">Clear Metrics</p>
              <p className="text-xs text-slate-500">Remove all time-series metrics data</p>
            </div>
          </div>
          <button
            onClick={() => clearData('metrics')}
            disabled={clearing === 'metrics'}
            className={clsx(
              'flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              confirmClear === 'metrics'
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30'
            )}
          >
            {clearing === 'metrics' ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : confirmClear === 'metrics' ? (
              <>
                <AlertTriangle className="w-3 h-3" />
                Confirm
              </>
            ) : (
              <>
                <Trash2 className="w-3 h-3" />
                Clear
              </>
            )}
          </button>
        </div>

        {/* Clear Logs */}
        <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-blue-600" />
            <div>
              <p className="font-medium text-slate-900 dark:text-white text-sm">Clear Request Logs</p>
              <p className="text-xs text-slate-500">Remove all request/response logs</p>
            </div>
          </div>
          <button
            onClick={() => clearData('logs')}
            disabled={clearing === 'logs'}
            className={clsx(
              'flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              confirmClear === 'logs'
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30'
            )}
          >
            {clearing === 'logs' ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : confirmClear === 'logs' ? (
              <>
                <AlertTriangle className="w-3 h-3" />
                Confirm
              </>
            ) : (
              <>
                <Trash2 className="w-3 h-3" />
                Clear
              </>
            )}
          </button>
        </div>

        {/* Clear All */}
        <div className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/30 rounded-lg">
          <div className="flex items-center gap-3">
            <Database className="w-5 h-5 text-red-600" />
            <div>
              <p className="font-medium text-red-900 dark:text-red-400 text-sm">Reset All Data</p>
              <p className="text-xs text-red-600/70 dark:text-red-400/70">Clear all metrics, logs, and reset model stats</p>
            </div>
          </div>
          <button
            onClick={() => clearData('all')}
            disabled={clearing === 'all'}
            className={clsx(
              'flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
              confirmClear === 'all'
                ? 'bg-red-700 text-white hover:bg-red-800'
                : 'bg-red-600 text-white hover:bg-red-700'
            )}
          >
            {clearing === 'all' ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : confirmClear === 'all' ? (
              <>
                <AlertTriangle className="w-3 h-3" />
                Confirm Reset
              </>
            ) : (
              <>
                <Trash2 className="w-3 h-3" />
                Reset All
              </>
            )}
          </button>
        </div>

        {confirmClear && (
          <p className="text-xs text-red-600 dark:text-red-400 text-center">
            Click again to confirm. This action cannot be undone.
          </p>
        )}
      </div>
    </div>
  )
}

/**
 * Settings page component.
 */
export function Settings() {
  const { theme, setTheme } = useThemeContext()
  const {
    refreshInterval,
    updateRefreshInterval,
    autoRefreshEnabled,
    toggleAutoRefresh,
  } = useAppContext()

  const [notifications, setNotifications] = useState(true)

  const themeOptions = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
  ]

  const refreshOptions = [
    { value: 1000, label: '1 second' },
    { value: 5000, label: '5 seconds' },
    { value: 10000, label: '10 seconds' },
    { value: 30000, label: '30 seconds' },
    { value: 60000, label: '1 minute' },
  ]

  const handleExportConfig = () => {
    const config = {
      theme,
      refreshInterval,
      autoRefreshEnabled,
      notifications,
      exportedAt: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'ollama-monitor-settings.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    showSuccess('Settings exported successfully')
  }

  const handleResetSettings = () => {
    setTheme('light')
    updateRefreshInterval(DEFAULT_REFRESH_INTERVAL)
    setNotifications(true)
    showSuccess('Settings reset to defaults')
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Settings
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Customize your dashboard experience
        </p>
      </div>

      {/* Appearance */}
      <SettingsSection
        title="Appearance"
        description="Customize how the dashboard looks"
      >
        <SettingsOption
          icon={Sun}
          label="Theme"
          description="Choose your preferred color scheme"
        >
          <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-700 rounded-lg">
            {themeOptions.map((option) => {
              const Icon = option.icon
              return (
                <button
                  key={option.value}
                  onClick={() => setTheme(option.value)}
                  className={clsx(
                    'flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-colors',
                    theme === option.value
                      ? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {option.label}
                </button>
              )
            })}
          </div>
        </SettingsOption>
      </SettingsSection>

      {/* Data & Refresh */}
      <SettingsSection
        title="Data & Refresh"
        description="Control how data is fetched and updated"
      >
        <SettingsOption
          icon={RefreshCw}
          label="Auto Refresh"
          description="Automatically refresh data at regular intervals"
        >
          <button
            onClick={toggleAutoRefresh}
            className={clsx(
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
              autoRefreshEnabled
                ? 'bg-blue-600'
                : 'bg-slate-300 dark:bg-slate-600'
            )}
          >
            <span
              className={clsx(
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                autoRefreshEnabled ? 'translate-x-6' : 'translate-x-1'
              )}
            />
          </button>
        </SettingsOption>

        <SettingsOption
          icon={RefreshCw}
          label="Refresh Interval"
          description="How often to fetch new data"
        >
          <select
            value={refreshInterval}
            onChange={(e) => updateRefreshInterval(Number(e.target.value))}
            disabled={!autoRefreshEnabled}
            className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-700 text-slate-900 dark:text-white disabled:opacity-50"
          >
            {refreshOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </SettingsOption>
      </SettingsSection>

      {/* Model Management */}
      <SettingsSection
        title="Model Management"
        description="Manage installed Ollama models and download new ones"
      >
        <ModelManagementSection />
      </SettingsSection>

      {/* Data Management */}
      <SettingsSection
        title="Data Management"
        description="View database usage and clear stored data"
      >
        <DataManagementSection />
      </SettingsSection>

      {/* Notifications */}
      <SettingsSection
        title="Notifications"
        description="Configure notification preferences"
      >
        <SettingsOption
          icon={Bell}
          label="Enable Notifications"
          description="Show toast notifications for events"
        >
          <button
            onClick={() => setNotifications(!notifications)}
            className={clsx(
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
              notifications
                ? 'bg-blue-600'
                : 'bg-slate-300 dark:bg-slate-600'
            )}
          >
            <span
              className={clsx(
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                notifications ? 'translate-x-6' : 'translate-x-1'
              )}
            />
          </button>
        </SettingsOption>
      </SettingsSection>

      {/* Data Management */}
      <SettingsSection
        title="Data Management"
        description="Export settings and reset preferences"
      >
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleExportConfig}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
          >
            <Download className="h-4 w-4" />
            Export Settings
          </button>
          <button
            onClick={handleResetSettings}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
          >
            Reset to Defaults
          </button>
        </div>
      </SettingsSection>

      {/* About */}
      <SettingsSection title="About">
        <div className="text-sm text-slate-600 dark:text-slate-400 space-y-2">
          <p>
            <span className="font-medium text-slate-900 dark:text-white">
              Ollama Monitor
            </span>{' '}
            v1.0.0
          </p>
          <p>
            A professional monitoring dashboard for Ollama Local Serve.
          </p>
          <p>
            Built with React, TailwindCSS, and Recharts.
          </p>
        </div>
      </SettingsSection>
    </motion.div>
  )
}

export default Settings
