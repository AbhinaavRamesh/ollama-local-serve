/**
 * Request log table with sorting, filtering, and pagination.
 */

import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
} from '@tanstack/react-table'
import {
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Download,
  Filter,
  X,
} from 'lucide-react'
import { formatTimestamp, formatDuration, truncate } from '../../utils/formatters'
import { StatusBadge } from '../dashboard/StatusIndicator'
import { TableSkeleton } from '../ui/LoadingSkeleton'
import { NoLogsState } from '../ui/EmptyState'

/**
 * Request log table component.
 * @param {Object} props
 * @param {Array} props.logs - Log entries
 * @param {boolean} props.loading - Loading state
 * @param {number} props.total - Total log count
 * @param {number} props.page - Current page
 * @param {number} props.pageSize - Page size
 * @param {Function} props.onPageChange - Page change handler
 * @param {Function} props.onPageSizeChange - Page size change handler
 * @param {Object} props.filters - Current filters
 * @param {Function} props.onFilterChange - Filter change handler
 * @param {Function} props.onExport - Export handler
 */
export function RequestLog({
  logs = [],
  loading = false,
  total = 0,
  page = 1,
  pageSize = 25,
  onPageChange,
  onPageSizeChange,
  filters = {},
  onFilterChange,
  onExport,
}) {
  const [sorting, setSorting] = useState([])
  const [expandedRows, setExpandedRows] = useState({})
  const [showFilters, setShowFilters] = useState(false)

  // Define columns
  const columns = useMemo(
    () => [
      {
        accessorKey: 'timestamp',
        header: 'Timestamp',
        cell: ({ getValue }) => (
          <span className="text-sm text-slate-600 dark:text-slate-400 whitespace-nowrap">
            {formatTimestamp(getValue(), 'MMM d, HH:mm:ss')}
          </span>
        ),
      },
      {
        accessorKey: 'model',
        header: 'Model',
        cell: ({ getValue }) => (
          <span className="text-sm font-medium text-slate-900 dark:text-white">
            {getValue()}
          </span>
        ),
      },
      {
        accessorKey: 'tokens',
        header: 'Tokens',
        cell: ({ getValue }) => (
          <span className="text-sm text-slate-600 dark:text-slate-400">
            {getValue()?.toLocaleString() || 0}
          </span>
        ),
      },
      {
        accessorKey: 'latency',
        header: 'Latency',
        cell: ({ getValue }) => {
          const value = getValue()
          const color =
            value > 1000
              ? 'text-red-600 dark:text-red-400'
              : value > 500
              ? 'text-amber-600 dark:text-amber-400'
              : 'text-emerald-600 dark:text-emerald-400'
          return (
            <span className={clsx('text-sm font-medium', color)}>
              {formatDuration(value)}
            </span>
          )
        },
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ getValue }) => {
          const status = getValue()
          return (
            <StatusBadge status={status === 'success' ? 'success' : 'error'}>
              {status}
            </StatusBadge>
          )
        },
      },
      {
        accessorKey: 'request_id',
        header: 'Request ID',
        cell: ({ getValue }) => (
          <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
            {truncate(getValue(), 12)}
          </span>
        ),
      },
    ],
    []
  )

  // React Table instance
  const table = useReactTable({
    data: logs,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
    pageCount: Math.ceil(total / pageSize),
  })

  // Toggle row expansion
  const toggleRow = (id) => {
    setExpandedRows((prev) => ({
      ...prev,
      [id]: !prev[id],
    }))
  }

  // Calculate pagination
  const totalPages = Math.ceil(total / pageSize)
  const startItem = (page - 1) * pageSize + 1
  const endItem = Math.min(page * pageSize, total)

  if (loading) {
    return <TableSkeleton rows={5} columns={6} />
  }

  if (logs.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
        <NoLogsState />
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h3 className="text-base font-semibold text-slate-900 dark:text-white">
            Request Logs
          </h3>
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {total.toLocaleString()} total
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={clsx(
              'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors',
              showFilters
                ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
            )}
          >
            <Filter className="h-4 w-4" />
            Filters
          </button>
          {onExport && (
            <button
              onClick={onExport}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <Download className="h-4 w-4" />
              Export
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm text-slate-600 dark:text-slate-400">
                Status:
              </label>
              <select
                value={filters.status || ''}
                onChange={(e) =>
                  onFilterChange?.({ ...filters, status: e.target.value || undefined })
                }
                className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
              >
                <option value="">All</option>
                <option value="success">Success</option>
                <option value="error">Error</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-slate-600 dark:text-slate-400">
                Model:
              </label>
              <input
                type="text"
                value={filters.model || ''}
                onChange={(e) =>
                  onFilterChange?.({ ...filters, model: e.target.value || undefined })
                }
                placeholder="Filter by model"
                className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1 bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400"
              />
            </div>
            {(filters.status || filters.model) && (
              <button
                onClick={() => onFilterChange?.({})}
                className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              >
                <X className="h-3 w-3" />
                Clear
              </button>
            )}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr
                key={headerGroup.id}
                className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50"
              >
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className={clsx(
                      'px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider',
                      header.column.getCanSort() && 'cursor-pointer select-none'
                    )}
                  >
                    <div className="flex items-center gap-1">
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext()
                      )}
                      {header.column.getIsSorted() === 'asc' && (
                        <ChevronUp className="h-4 w-4" />
                      )}
                      {header.column.getIsSorted() === 'desc' && (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => {
              const log = row.original
              const isExpanded = expandedRows[log.request_id]

              return (
                <>
                  <tr
                    key={row.id}
                    onClick={() => log.error_message && toggleRow(log.request_id)}
                    className={clsx(
                      'border-b border-slate-200 dark:border-slate-700 transition-colors',
                      log.error_message && 'cursor-pointer',
                      isExpanded
                        ? 'bg-slate-50 dark:bg-slate-800/50'
                        : 'hover:bg-slate-50 dark:hover:bg-slate-800/30'
                    )}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    ))}
                  </tr>
                  {isExpanded && log.error_message && (
                    <tr className="bg-red-50 dark:bg-red-900/10">
                      <td colSpan={columns.length} className="px-4 py-3">
                        <div className="text-sm">
                          <span className="font-medium text-red-700 dark:text-red-400">
                            Error:{' '}
                          </span>
                          <span className="text-red-600 dark:text-red-300">
                            {log.error_message}
                          </span>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-600 dark:text-slate-400">
            Showing {startItem} to {endItem} of {total}
          </span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange?.(Number(e.target.value))}
            className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
          >
            {[10, 25, 50, 100].map((size) => (
              <option key={size} value={size}>
                {size} per page
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onPageChange?.(1)}
            disabled={page === 1}
            className="p-1.5 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronsLeft className="h-4 w-4" />
          </button>
          <button
            onClick={() => onPageChange?.(page - 1)}
            disabled={page === 1}
            className="p-1.5 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="px-3 py-1 text-sm text-slate-600 dark:text-slate-400">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange?.(page + 1)}
            disabled={page >= totalPages}
            className="p-1.5 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
          <button
            onClick={() => onPageChange?.(totalPages)}
            disabled={page >= totalPages}
            className="p-1.5 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronsRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default RequestLog
