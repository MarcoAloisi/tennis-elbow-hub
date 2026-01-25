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

    // Filters & View Options
    const filters = ref({
        opponent: null,
        surface: null,
        tournament: null,
        sets: null, // '3', '5', or null
        cpu: true, // Hide CPU matches by default
        dateStart: null,
        dateEnd: null
    })

    const sortDesc = ref(true) // Default to Newest first
    const statsMode = ref('avg') // 'avg' or 'median'

    // Getters
    const hasMatches = computed(() => matches.value.length > 0)
    const currentMatch = computed(() => matches.value[currentMatchIndex.value] || null)

    const player1Stats = computed(() => currentMatch.value?.player1 || null)
    const player2Stats = computed(() => currentMatch.value?.player2 || null)
    const matchInfo = computed(() => currentMatch.value?.info || null)

    // Filtered Matches
    const filteredMatches = computed(() => {
        let result = matches.value.filter(match => {
            if (!match.info) return false
            const info = match.info

            // Filter by Opponent
            if (filters.value.opponent) {
                const opp = filters.value.opponent.toLowerCase()
                if (!info.player1_name.toLowerCase().includes(opp) &&
                    !info.player2_name.toLowerCase().includes(opp)) {
                    return false
                }
            }

            // Filter CPU Matches
            if (filters.value.cpu) {
                // Check for CPU indicators in opponent name (assuming User is Player 1, or check both)
                // CPU names often have levels like "Incredible-10", "Pro-1", "Master-5"
                // Or sometimes just ends with "-X"
                const cpuPatterns = [/Incredible-/i, /Pro-/i, /Master-/i, /Junior-/i, /Club-/i, /-\d+$/]
                const p1IsCpu = cpuPatterns.some(p => p.test(info.player1_name))
                const p2IsCpu = cpuPatterns.some(p => p.test(info.player2_name))

                // If we assume user is one of them, we usually want to hide matches vs CPU.
                // Usually the opponent name has the CPU tag.
                if (p1IsCpu || p2IsCpu) return false
            }

            // Filter by Surface
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

            // Filter by Sets
            if (filters.value.sets && info.score) {
                const score = info.score
                const isBestOf5 = score.includes('3/') || score.includes('/3') || score.includes('3-') || score.includes('-3')
                const setParts = score.split(' ').filter(s => s.includes('/') || s.includes('-'))
                const numSets = setParts.length

                if (filters.value.sets === '5' && !isBestOf5) return false
                if (filters.value.sets === '3' && (isBestOf5 || numSets === 1)) return false
                if (filters.value.sets === '1' && numSets > 1) return false
            }

            // Filter by Date
            if (filters.value.dateStart || filters.value.dateEnd) {
                if (!info.date) return false
                const matchDate = new Date(info.date)
                if (filters.value.dateStart && matchDate < new Date(filters.value.dateStart)) return false
                if (filters.value.dateEnd) {
                    const endDate = new Date(filters.value.dateEnd)
                    endDate.setHours(23, 59, 59, 999) // End of day
                    if (matchDate > endDate) return false
                }
            }

            return true
        })

        // Sorting
        result.sort((a, b) => {
            const dateA = a.info?.date ? new Date(a.info.date) : new Date(0)
            const dateB = b.info?.date ? new Date(b.info.date) : new Date(0)
            return sortDesc.value ? dateB - dateA : dateA - dateB
        })

        return result
    })

    // Helper for median calculation
    function calculateMedian(values) {
        if (values.length === 0) return 0
        values.sort((a, b) => a - b)
        const half = Math.floor(values.length / 2)
        if (values.length % 2) return values[half]
        return (values[half - 1] + values[half]) / 2.0
    }

    // Comprehensive Aggregates
    const aggregateStats = computed(() => {
        const list = filteredMatches.value
        if (!list.length) return null

        // metrics to collect
        const metrics = {
            matches: [],
            // Serve
            first_serve_pct: [],
            aces: [],
            double_faults: [],
            fastest_serve: [],
            avg_first_serve: [],
            avg_second_serve: [],
            first_serve_won_pct: [],
            second_serve_won_pct: [],
            // Rally
            short_rally_won_pct: [],
            medium_rally_won_pct: [],
            long_rally_won_pct: [],
            avg_rally_length: [],
            // Points
            winners: [],
            forced_errors: [],
            unforced_errors: [],
            net_points_won_pct: [],
            return_points_won_pct: [],
            return_winners: [],
            total_points_won_pct: [],
            // Breaks
            break_points_won_pct: [],
            break_games_won_pct: [],
            set_points_saved: [],
            match_points_saved: []
        }

        list.forEach(m => {
            const p1 = m.player1
            if (p1) {
                // Serve
                metrics.first_serve_pct.push(p1.serve.first_serve_pct)
                metrics.aces.push(p1.serve.aces)
                metrics.double_faults.push(p1.serve.double_faults)
                if (p1.serve.fastest_serve_kmh) metrics.fastest_serve.push(p1.serve.fastest_serve_kmh)
                if (p1.serve.avg_first_serve_kmh) metrics.avg_first_serve.push(p1.serve.avg_first_serve_kmh)
                if (p1.serve.avg_second_serve_kmh) metrics.avg_second_serve.push(p1.serve.avg_second_serve_kmh)
                metrics.first_serve_won_pct.push(p1.points.points_on_first_serve_won / p1.points.points_on_first_serve_total * 100 || 0)
                metrics.second_serve_won_pct.push(p1.points.points_on_second_serve_won / p1.points.points_on_second_serve_total * 100 || 0)

                // Rally - calculate percentages for won/total if total > 0
                if (p1.rally.short_rallies_total > 0) metrics.short_rally_won_pct.push(p1.rally.short_rallies_won / p1.rally.short_rallies_total * 100)
                if (p1.rally.normal_rallies_total > 0) metrics.medium_rally_won_pct.push(p1.rally.normal_rallies_won / p1.rally.normal_rallies_total * 100)
                if (p1.rally.long_rallies_total > 0) metrics.long_rally_won_pct.push(p1.rally.long_rallies_won / p1.rally.long_rallies_total * 100)
                if (p1.rally.avg_rally_length > 0) metrics.avg_rally_length.push(p1.rally.avg_rally_length)

                // Points
                metrics.winners.push(p1.points.winners)
                metrics.forced_errors.push(p1.points.forced_errors)
                metrics.unforced_errors.push(p1.points.unforced_errors)
                if (p1.points.net_points_total > 0) metrics.net_points_won_pct.push(p1.points.net_points_won / p1.points.net_points_total * 100)
                if (p1.points.return_points_total > 0) metrics.return_points_won_pct.push(p1.points.return_points_won / p1.points.return_points_total * 100)
                metrics.return_winners.push(p1.points.return_winners)
                metrics.total_points_won_pct.push(p1.points.total_points_won / (p1.points.total_points_won + (m.player2?.points?.total_points_won || 0)) * 100 || 0)

                // Breaks
                if (p1.break_points.break_points_total > 0) metrics.break_points_won_pct.push(p1.break_points.break_points_won / p1.break_points.break_points_total * 100)
                if (p1.break_points.break_games_total > 0) metrics.break_games_won_pct.push(p1.break_points.break_games_won / p1.break_points.break_games_total * 100)
                metrics.set_points_saved.push(p1.break_points.set_points_saved)
                metrics.match_points_saved.push(p1.break_points.match_points_saved)
            }
        })

        const result = {}
        const mode = statsMode.value

        Object.keys(metrics).forEach(key => {
            if (key === 'matches') return
            const values = metrics[key]
            if (values.length === 0) {
                result[key] = 0
                return
            }

            if (mode === 'avg') {
                const sum = values.reduce((a, b) => a + b, 0)
                result[key] = (sum / values.length).toFixed(1)
            } else {
                result[key] = calculateMedian(values).toFixed(1)
            }
        })

        result.totalMatches = list.length
        return result
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
            sets: null,
            cpu: true,
            dateStart: null,
            dateEnd: null
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
        sortDesc,
        statsMode,
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
