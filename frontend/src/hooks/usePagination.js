/**
 * Custom hook for handling pagination.
 */

import { useState, useMemo, useCallback } from 'react'

/**
 * Hook for managing pagination state.
 * @param {number} totalItems - Total number of items
 * @param {number} initialPageSize - Initial page size
 * @returns {Object} Pagination state and handlers
 */
export function usePagination(totalItems = 0, initialPageSize = 25) {
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(initialPageSize)

  // Calculate total pages
  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil(totalItems / pageSize))
  }, [totalItems, pageSize])

  // Calculate offset for API calls
  const offset = useMemo(() => {
    return (currentPage - 1) * pageSize
  }, [currentPage, pageSize])

  // Get page range for display
  const pageRange = useMemo(() => {
    const start = offset + 1
    const end = Math.min(offset + pageSize, totalItems)
    return { start, end }
  }, [offset, pageSize, totalItems])

  // Navigation handlers
  const goToPage = useCallback(
    (page) => {
      const newPage = Math.max(1, Math.min(page, totalPages))
      setCurrentPage(newPage)
    },
    [totalPages]
  )

  const nextPage = useCallback(() => {
    goToPage(currentPage + 1)
  }, [currentPage, goToPage])

  const prevPage = useCallback(() => {
    goToPage(currentPage - 1)
  }, [currentPage, goToPage])

  const firstPage = useCallback(() => {
    goToPage(1)
  }, [goToPage])

  const lastPage = useCallback(() => {
    goToPage(totalPages)
  }, [goToPage, totalPages])

  // Change page size (resets to page 1)
  const changePageSize = useCallback((newSize) => {
    setPageSize(newSize)
    setCurrentPage(1)
  }, [])

  // Reset pagination
  const reset = useCallback(() => {
    setCurrentPage(1)
  }, [])

  // Check if navigation is possible
  const canPrevPage = currentPage > 1
  const canNextPage = currentPage < totalPages

  // Generate page numbers for pagination UI
  const pageNumbers = useMemo(() => {
    const pages = []
    const maxVisible = 7

    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i)
      }
    } else {
      // Always show first page
      pages.push(1)

      // Calculate range around current page
      let start = Math.max(2, currentPage - 2)
      let end = Math.min(totalPages - 1, currentPage + 2)

      // Adjust range if at edges
      if (currentPage <= 3) {
        end = 5
      } else if (currentPage >= totalPages - 2) {
        start = totalPages - 4
      }

      // Add ellipsis if needed
      if (start > 2) {
        pages.push('...')
      }

      // Add middle pages
      for (let i = start; i <= end; i++) {
        pages.push(i)
      }

      // Add ellipsis if needed
      if (end < totalPages - 1) {
        pages.push('...')
      }

      // Always show last page
      pages.push(totalPages)
    }

    return pages
  }, [totalPages, currentPage])

  return {
    currentPage,
    pageSize,
    totalPages,
    offset,
    pageRange,
    pageNumbers,
    canPrevPage,
    canNextPage,
    goToPage,
    nextPage,
    prevPage,
    firstPage,
    lastPage,
    changePageSize,
    reset,
  }
}

export default usePagination
