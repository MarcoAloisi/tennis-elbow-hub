/**
 * Debounced search composable
 * Provides a reactive search query with configurable debounce delay.
 * Replaces manual setTimeout/clearTimeout patterns.
 */
import { ref, watch, onUnmounted } from 'vue'

/**
 * @param {Function} onSearch - Callback invoked with the debounced query value
 * @param {Object} options
 * @param {number} options.delay - Debounce delay in ms (default: 300)
 * @param {string} options.initialValue - Initial search query (default: '')
 */
export function useDebouncedSearch(onSearch, { delay = 300, initialValue = '' } = {}) {
    const searchQuery = ref(initialValue)
    let timer = null

    function clearTimer() {
        if (timer) {
            clearTimeout(timer)
            timer = null
        }
    }

    watch(searchQuery, (newVal) => {
        clearTimer()
        timer = setTimeout(() => {
            onSearch(newVal)
        }, delay)
    })

    function clear() {
        searchQuery.value = ''
    }

    onUnmounted(clearTimer)

    return {
        searchQuery,
        clear
    }
}
