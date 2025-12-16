/**
 * Logs page - request logs with filtering and pagination.
 */

import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Download } from 'lucide-react'
import { RequestLog } from '../components/tables/RequestLog'
import { useFetchStats } from '../hooks/useFetchStats'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { usePagination } from '../hooks/usePagination'
import { useAppContext } from '../context/AppContext'
import { fetchLogs, exportLogsCSV } from '../utils/api'
import { showSuccess, showError } from '../components/ui/Toast'

/**
 * Logs page component.
 */
export function Logs() {
  const [filters, setFilters] = useState({})
  const { refreshInterval } = useAppContext()

  // Pagination
  const pagination = usePagination(0, 25)

  // Fetch logs
  const {
    data: logsData,
    loading,
    error,
    refetch,
  } = useFetchStats(
    () =>
      fetchLogs({
        limit: pagination.pageSize,
        offset: pagination.offset,
        ...filters,
      }),
    {
      staleTime: 5000,
      deps: [pagination.currentPage, pagination.pageSize, filters],
    }
  )

  // Update total for pagination
  if (logsData?.total !== undefined && logsData.total !== pagination.totalPages * pagination.pageSize) {
    // Total changed, but we can't update pagination state here directly
    // This is handled by the pagination component itself
  }

  // Auto-refresh
  useAutoRefresh(refetch, refreshInterval)

  // Handle page change
  const handlePageChange = (page) => {
    pagination.goToPage(page)
  }

  // Handle page size change
  const handlePageSizeChange = (size) => {
    pagination.changePageSize(size)
  }

  // Handle filter change
  const handleFilterChange = (newFilters) => {
    setFilters(newFilters)
    pagination.reset()
  }

  // Handle export
  const handleExport = async () => {
    try {
      const blob = await exportLogsCSV(filters)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ollama-logs-${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      showSuccess('Logs exported successfully')
    } catch (err) {
      showError('Failed to export logs')
      console.error('Export error:', err)
    }
  }

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
            Request Logs
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            View and analyze request history
          </p>
        </div>
      </div>

      {/* Logs Table */}
      <RequestLog
        logs={logsData?.logs || []}
        loading={loading}
        total={logsData?.total || 0}
        page={pagination.currentPage}
        pageSize={pagination.pageSize}
        onPageChange={handlePageChange}
        onPageSizeChange={handlePageSizeChange}
        filters={filters}
        onFilterChange={handleFilterChange}
        onExport={handleExport}
      />
    </motion.div>
  )
}

export default Logs
