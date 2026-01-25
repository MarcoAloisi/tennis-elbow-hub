/**
 * Pinia store for match analysis
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiUrl } from '@/config/api'

export const useAnalysisStore = defineStore('analysis', () => {
    // State
    const matches = ref([])
    const currentMatchIndex = ref(0)
    const analysisHistory = ref([])
    const isLoading = ref(false)
    const error = ref(null)
    const uploadProgress = ref(0)

    // Filters
    const filters = ref({
        opponent: null,
        surface: null,
        tournament: null,
        sets: null // '3', '5', or null
    })

    // Getters
    const hasMatches = computed(() => matches.value.length > 0)
    const currentMatch = computed(() => matches.value[currentMatchIndex.value] || null)

    const player1Stats = computed(() => currentMatch.value?.player1 || null)
    const player2Stats = computed(() => currentMatch.value?.player2 || null)
    const matchInfo = computed(() => currentMatch.value?.info || null)

    // Filtered Matches
    const filteredMatches = computed(() => {
        return matches.value.filter(match => {
            if (!match.info) return false
            const info = match.info

            // Filter by Opponent (either player name matches)
            if (filters.value.opponent) {
                const opp = filters.value.opponent.toLowerCase()
                if (!info.player1_name.toLowerCase().includes(opp) &&
                    !info.player2_name.toLowerCase().includes(opp)) {
                    return false
                }
            }

            // Filter by Surface (assuming surface is part of tournament name or separate metadata if available)
            // Note: Parser currently extracts "Tournament", surface might need inference or better parsing
            if (filters.value.surface && info.tournament) {
                if (!info.tournament.toLowerCase().includes(filters.value.surface.toLowerCase())) {
                    return false
                }
            }

            // Filter by Tournament
            if (filters.value.tournament && info.tournament) {
                if (!info.tournament.toLowerCase().includes(filters.value.tournament.toLowerCase())) {
                    return false
                }
            }

            return true
        })
    })

    // Aggregates
    const aggregateStats = computed(() => {
        const list = filteredMatches.value
        if (!list.length) return null

        let totalAces = 0
        let totalDoubleFaults = 0
        let totalWinners = 0
        let totalUnforcedErrors = 0
        let totalMatches = list.length

        list.forEach(m => {
            // Aggregate stats for the "Main Player" (Player 1 usually, or logic to detect user)
            // For now assuming Player 1 is the user
            const p1 = m.player1
            if (p1) {
                totalAces += p1.serve.aces
                totalDoubleFaults += p1.serve.double_faults
                totalWinners += p1.points.winners
                totalUnforcedErrors += p1.points.unforced_errors
            }
        })

        return {
            totalMatches,
            avgAces: (totalAces / totalMatches).toFixed(1),
            avgDoubleFaults: (totalDoubleFaults / totalMatches).toFixed(1),
            avgWinners: (totalWinners / totalMatches).toFixed(1),
            avgUnforcedErrors: (totalUnforcedErrors / totalMatches).toFixed(1)
        }
    })

    // Actions
    async function uploadAndAnalyze(file) {
        isLoading.value = true
        error.value = null
        uploadProgress.value = 0

        try {
            const formData = new FormData()
            formData.append('file', file)

            const response = await fetch(apiUrl('/api/analysis/upload'), {
                method: 'POST',
                body: formData
            })

            uploadProgress.value = 100

            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(errorData.detail || `HTTP error ${response.status}`)
            }

            const data = await response.json()

            if (data.success) {
                matches.value = data.matches || []
                currentMatchIndex.value = 0

                // Add to history
                analysisHistory.value.unshift({
                    filename: data.filename,
                    matchCount: matches.value.length,
                    uploadedAt: new Date().toISOString()
                })
                // Keep only last 10 analyses
                if (analysisHistory.value.length > 10) {
                    analysisHistory.value.pop()
                }
            } else {
                throw new Error(data.error || 'Analysis failed')
            }

            return data
        } catch (e) {
            error.value = e.message
            console.error('Failed to analyze file:', e)
            throw e
        } finally {
            isLoading.value = false
        }
    }

    async function loadSampleAnalysis() {
        isLoading.value = true
        error.value = null

        try {
            const response = await fetch(apiUrl('/api/analysis/sample'))

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`)
            }

            const data = await response.json()
            matches.value = data.matches || []
            currentMatchIndex.value = 0
            return data
        } catch (e) {
            error.value = e.message
            console.error('Failed to load sample:', e)
            throw e
        } finally {
            isLoading.value = false
        }
    }

    function clearAnalysis() {
        matches.value = []
        currentMatchIndex.value = 0
        error.value = null
    }

    function selectMatch(index) {
        if (index >= 0 && index < matches.value.length) {
            currentMatchIndex.value = index
        }
    }

    function loadFromHistory(index) {
        // Implementation for reloading previous files would require storing full data or re-fetching
        // For now this is valid for the session
    }

    function setFilter(key, value) {
        filters.value[key] = value
    }

    function clearFilters() {
        filters.value = {
            opponent: null,
            surface: null,
            tournament: null,
            sets: null
        }
    }

    return {
        // State
        matches,
        currentMatchIndex,
        analysisHistory,
        isLoading,
        error,
        uploadProgress,
        // Getters
        hasMatches,
        currentMatch,
        player1Stats,
        player2Stats,
        matchInfo,
        filteredMatches,
        aggregateStats,
        filters,
        // Actions
        uploadAndAnalyze,
        loadSampleAnalysis,
        clearAnalysis,
        selectMatch,
        setFilter,
        clearFilters
    }
})
