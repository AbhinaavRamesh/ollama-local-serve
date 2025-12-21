/**
 * Request log table with sorting, filtering, pagination, and expandable details.
 */

import { useState, useMemo, Fragment } from 'react'
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
  Eye,
  Copy,
  Check,
  Globe,
  Monitor,
  User,
  MessageSquare,
  Bot,
  Clock,
  Zap,
} from 'lucide-react'
import { formatTimestamp, formatDuration, truncate } from '../../utils/formatters'
import { StatusBadge } from '../dashboard/StatusIndicator'
import { TableSkeleton } from '../ui/LoadingSkeleton'
import { NoLogsState } from '../ui/EmptyState'

/**
 * Copy to clipboard button.
 */
function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async (e) => {
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
      title={`Copy ${label}`}
    >
      {copied ? (
        <>
          <Check className="w-3 h-3 text-green-500" />
          Copied
        </>
      ) : (
        <>
          <Copy className="w-3 h-3" />
          Copy
        </>
      )}
    </button>
  )
}

/**
 * Expandable log details panel.
 */
function LogDetails({ log }) {
  return (
    <div className="bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700">
      <div className="p-4 space-y-4">
        {/* Prompt & Response */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Prompt */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                <User className="w-4 h-4 text-blue-500" />
                Prompt
                {log.prompt_tokens > 0 && (
                  <span className="text-xs text-slate-500">({log.prompt_tokens} tokens)</span>
                )}
              </div>
              {log.prompt_text && <CopyButton text={log.prompt_text} label="prompt" />}
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-lg p-3 border border-slate-200 dark:border-slate-700 max-h-48 overflow-y-auto">
              <pre className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap break-words font-mono">
                {log.prompt_text || <span className="text-slate-400 italic">No prompt recorded</span>}
              </pre>
            </div>
          </div>

          {/* Response */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                <Bot className="w-4 h-4 text-purple-500" />
                Response
                {log.tokens > 0 && (
                  <span className="text-xs text-slate-500">({log.tokens} tokens)</span>
                )}
              </div>
              {log.response_text && <CopyButton text={log.response_text} label="response" />}
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-lg p-3 border border-slate-200 dark:border-slate-700 max-h-48 overflow-y-auto">
              <pre className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap break-words font-mono">
                {log.response_text || <span className="text-slate-400 italic">No response recorded</span>}
              </pre>
            </div>
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2 border-t border-slate-200 dark:border-slate-700">
          {/* Token Stats */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <Zap className="w-3 h-3" />
              Token Usage
            </div>
            <div className="text-sm text-slate-700 dark:text-slate-300">
              <span className="font-medium">{log.total_tokens || (log.prompt_tokens || 0) + (log.tokens || 0)}</span> total
              <span className="text-slate-400 mx-1">|</span>
              {log.prompt_tokens || 0} in / {log.tokens || 0} out
            </div>
          </div>

          {/* Latency */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <Clock className="w-3 h-3" />
              Performance
            </div>
            <div className="text-sm text-slate-700 dark:text-slate-300">
              <span className="font-medium">{formatDuration(log.latency)}</span>
              {log.tokens > 0 && log.latency > 0 && (
                <span className="text-slate-400 ml-1">
                  ({((log.tokens / log.latency) * 1000).toFixed(1)} tok/s)
                </span>
              )}
            </div>
          </div>

          {/* Client IP */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <Globe className="w-3 h-3" />
              Client IP
            </div>
            <div className="text-sm font-mono text-slate-700 dark:text-slate-300">
              {log.client_ip || <span className="text-slate-400">-</span>}
            </div>
          </div>

          {/* Origin */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <Monitor className="w-3 h-3" />
              Origin
            </div>
            <div className="text-sm text-slate-700 dark:text-slate-300 truncate">
              {log.origin || log.referer || <span className="text-slate-400">-</span>}
            </div>
          </div>
        </div>

        {/* User Agent */}
        {log.user_agent && (
          <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 mb-1">
              <Monitor className="w-3 h-3" />
              User Agent
            </div>
            <div className="text-xs font-mono text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-900 rounded p-2 border border-slate-200 dark:border-slate-700">
              {log.user_agent}
            </div>
          </div>
        )}

        {/* Error Message */}
        {log.error_message && (
          <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
            <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 border border-red-200 dark:border-red-800">
              <div className="text-sm font-medium text-red-700 dark:text-red-400 mb-1">Error</div>
              <div className="text-sm text-red-600 dark:text-red-300">{log.error_message}</div>
            </div>
          </div>
        )}

        {/* Request ID */}
        <div className="flex items-center gap-2 pt-2 border-t border-slate-200 dark:border-slate-700">
          <span className="text-xs text-slate-500">Request ID:</span>
          <code className="text-xs font-mono text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-900 px-2 py-0.5 rounded">
            {log.request_id}
          </code>
          <CopyButton text={log.request_id} label="request ID" />
        </div>
      </div>
    </div>
  )
}

/**
 * Request log table component.
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
        id: 'expand',
        header: '',
        size: 40,
        cell: ({ row }) => {
          const isExpanded = expandedRows[row.original.request_id]
          return (
            <button
              onClick={(e) => {
                e.stopPropagation()
                toggleRow(row.original.request_id)
              }}
              className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
            >
              <Eye className={clsx('w-4 h-4', isExpanded ? 'text-blue-500' : 'text-slate-400')} />
            </button>
          )
        },
      },
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
        accessorKey: 'prompt_text',
        header: 'Prompt',
        cell: ({ getValue }) => {
          const text = getValue()
          return (
            <span className="text-sm text-slate-600 dark:text-slate-400 max-w-[200px] truncate block">
              {text ? truncate(text, 50) : <span className="text-slate-400 italic">-</span>}
            </span>
          )
        },
      },
      {
        id: 'tokens_combined',
        header: 'Tokens',
        cell: ({ row }) => {
          const promptTokens = row.original.prompt_tokens || 0
          const genTokens = row.original.tokens || 0
          const total = row.original.total_tokens || (promptTokens + genTokens)
          return (
            <div className="text-sm">
              <span className="font-medium text-slate-900 dark:text-white">{total}</span>
              <span className="text-slate-400 text-xs ml-1">
                ({promptTokens}/{genTokens})
              </span>
            </div>
          )
        },
      },
      {
        accessorKey: 'latency',
        header: 'Latency',
        cell: ({ getValue }) => {
          const value = getValue()
          const color =
            value > 2000
              ? 'text-red-600 dark:text-red-400'
              : value > 1000
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
        accessorKey: 'client_ip',
        header: 'Client',
        cell: ({ getValue, row }) => {
          const ip = getValue()
          const origin = row.original.origin
          return (
            <div className="text-xs">
              <div className="font-mono text-slate-600 dark:text-slate-400">
                {ip || '-'}
              </div>
              {origin && (
                <div className="text-slate-400 truncate max-w-[120px]" title={origin}>
                  {origin.replace(/^https?:\/\//, '')}
                </div>
              )}
            </div>
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
    ],
    [expandedRows]
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
    return <TableSkeleton rows={5} columns={8} />
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
                    onClick={header.column.getCanSort() ? header.column.getToggleSortingHandler() : undefined}
                    className={clsx(
                      'px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider',
                      header.column.getCanSort() && 'cursor-pointer select-none hover:text-slate-700 dark:hover:text-slate-200'
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
                <Fragment key={row.id}>
                  <tr
                    onClick={() => toggleRow(log.request_id)}
                    className={clsx(
                      'border-b border-slate-200 dark:border-slate-700 transition-colors cursor-pointer',
                      isExpanded
                        ? 'bg-blue-50 dark:bg-blue-900/10'
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
                  {isExpanded && (
                    <tr>
                      <td colSpan={columns.length} className="p-0">
                        <LogDetails log={log} />
                      </td>
                    </tr>
                  )}
                </Fragment>
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
            Page {page} of {totalPages || 1}
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
