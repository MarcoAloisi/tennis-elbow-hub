/**
 * Pinia store for live scores
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiUrl } from '@/config/api'

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

    // Daily stats from backend API (finished matches only)
    const dailyStats = ref({
        date: null,
        xkt: { total: 0, bo1: 0, bo3: 0, bo5: 0 },
        wtsl: { total: 0, bo1: 0, bo3: 0, bo5: 0 },
        vanilla: { total: 0, bo1: 0, bo3: 0, bo5: 0 }
    })

    // Monthly average stats from backend API
    const monthlyStats = ref({
        date_range: null,
        days_recorded: 0,
        xkt: { avg_total: 0, avg_bo1: 0, avg_bo3: 0, avg_bo5: 0 },
        wtsl: { avg_total: 0, avg_bo1: 0, avg_bo3: 0, avg_bo5: 0 },
        vanilla: { avg_total: 0, avg_bo1: 0, avg_bo3: 0, avg_bo5: 0 }
    })

    // Top players for the month
    const topPlayers = ref([])

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

    // Total finished matches today
    const dailyStatsTotal = computed(() => {
        const s = dailyStats.value
        return s.xkt.total + s.wtsl.total + s.vanilla.total
    })

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

            const url = apiUrl(`/api/scores${params.toString() ? '?' + params.toString() : ''}`)
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

    async function fetchDailyStats() {
        try {
            const url = apiUrl('/api/scores/stats/today')
            const response = await fetch(url)

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`)
            }

            const data = await response.json()
            dailyStats.value = data
        } catch (e) {
            console.error('Failed to fetch daily stats:', e)
        }
    }

    async function fetchMonthlyStats() {
        try {
            const url = apiUrl('/api/scores/stats/monthly')
            const response = await fetch(url)

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`)
            }

            const data = await response.json()
            monthlyStats.value = data
        } catch (e) {
            console.error('Failed to fetch monthly stats:', e)
        }
    }

    async function fetchTopPlayers() {
        try {
            const url = apiUrl('/api/scores/stats/top-players')
            const response = await fetch(url)

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`)
            }

            const data = await response.json()
            topPlayers.value = data
        } catch (e) {
            console.error('Failed to fetch top players:', e)
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

    // Expose stats as alias to dailyStats for template compatibility
    const stats = computed(() => dailyStats.value)

    return {
        // State
        servers,
        isLoading,
        error,
        lastUpdated,
        filters,
        dailyStats,
        monthlyStats,
        topPlayers,
        // Getters
        filteredServers,
        serverCount,
        activeMatchCount,
        dailyStatsTotal,
        stats,
        // Actions
        fetchScores,
        fetchDailyStats,
        fetchMonthlyStats,
        fetchTopPlayers,
        updateFromWebSocket,
        setFilter,
        clearFilters
    }
})

