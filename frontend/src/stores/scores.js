/**
 * Pinia store for live scores
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useScoresStore = defineStore('scores', () => {
    // State
    const servers = ref([])
    const isLoading = ref(false)
    const error = ref(null)
    const lastUpdated = ref(null)
    const filters = ref({
        surface: null,
        startedOnly: false,
        minElo: null,
        maxElo: null,
        searchQuery: ''
    })

    // Getters
    const filteredServers = computed(() => {
        let result = servers.value

        if (filters.value.searchQuery) {
            const query = filters.value.searchQuery.toLowerCase()
            result = result.filter(s =>
                s.match_name.toLowerCase().includes(query) ||
                s.surface_name.toLowerCase().includes(query)
            )
        }

        if (filters.value.surface) {
            result = result.filter(s =>
                s.surface_name.toLowerCase().includes(filters.value.surface.toLowerCase())
            )
        }

        if (filters.value.startedOnly) {
            result = result.filter(s => s.is_started)
        }

        if (filters.value.minElo !== null) {
            result = result.filter(s => s.elo >= filters.value.minElo)
        }

        if (filters.value.maxElo !== null) {
            result = result.filter(s => s.elo <= filters.value.maxElo)
        }

        return result
    })

    const serverCount = computed(() => servers.value.length)
    const activeMatchCount = computed(() => servers.value.filter(s => s.is_started).length)

    // Actions
    async function fetchScores() {
        isLoading.value = true
        error.value = null

        try {
            const params = new URLSearchParams()
            if (filters.value.surface) params.append('surface', filters.value.surface)
            if (filters.value.startedOnly) params.append('started_only', 'true')
            if (filters.value.minElo) params.append('min_elo', filters.value.minElo)
            if (filters.value.maxElo) params.append('max_elo', filters.value.maxElo)

            const url = `/api/scores${params.toString() ? '?' + params.toString() : ''}`
            const response = await fetch(url)

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`)
            }

            const data = await response.json()
            servers.value = data.servers || []
            lastUpdated.value = new Date().toISOString()
        } catch (e) {
            error.value = e.message
            console.error('Failed to fetch scores:', e)
        } finally {
            isLoading.value = false
        }
    }

    function updateFromWebSocket(data) {
        if (data && data.servers) {
            servers.value = data.servers
            lastUpdated.value = data.timestamp || new Date().toISOString()
            error.value = null
        }
    }

    function setFilter(key, value) {
        filters.value[key] = value
    }

    function clearFilters() {
        filters.value = {
            surface: null,
            startedOnly: false,
            minElo: null,
            maxElo: null,
            searchQuery: ''
        }
    }

    return {
        // State
        servers,
        isLoading,
        error,
        lastUpdated,
        filters,
        // Getters
        filteredServers,
        serverCount,
        activeMatchCount,
        // Actions
        fetchScores,
        updateFromWebSocket,
        setFilter,
        clearFilters
    }
})
