/**
 * Pagination composable
 * Provides page number generation and navigation helpers.
 * Replaces duplicated pagination logic in GuidesView and OutfitGalleryView.
 */
import { computed } from 'vue'

/**
 * @param {Object} options
 * @param {Function} options.currentPage - Getter returning the current page number
 * @param {Function} options.totalPages - Getter returning total number of pages
 * @param {Function} options.totalItems - Getter returning total item count
 * @param {number} options.pageSize - Items per page (default: 12)
 * @param {Function} options.onPageChange - Callback invoked when page changes
 */
export function usePagination({ currentPage, totalPages, totalItems, pageSize = 12, onPageChange }) {
    /**
     * Generate smart page number array with ellipsis
     */
    const pageNumbers = computed(() => {
        const total = totalPages()
        const current = currentPage()
        if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)

        const pages: (number | string)[] = [1]
        if (current > 3) pages.push('...')
        const start = Math.max(2, current - 1)
        const end = Math.min(total - 1, current + 1)
        for (let i = start; i <= end; i++) pages.push(i)
        if (current < total - 2) pages.push('...')
        pages.push(total)
        return pages
    })

    /**
     * Range text: "Showing X–Y of Z"
     */
    const showingRange = computed(() => {
        const page = currentPage()
        const total = totalItems()
        const from = total === 0 ? 0 : (page - 1) * pageSize + 1
        const to = Math.min(page * pageSize, total)
        return { from, to, total }
    })

    /**
     * Navigate to a specific page
     */
    function goToPage(page) {
        const total = totalPages()
        if (page < 1 || page > total) return
        onPageChange(page)
    }

    return {
        pageNumbers,
        showingRange,
        goToPage
    }
}
