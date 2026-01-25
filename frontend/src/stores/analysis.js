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

    // Automatic User Detection: Find the player name that appears most frequently
    const mainPlayerName = computed(() => {
        if (!matches.value.length) return 'Player'
        const names = {}
        matches.value.forEach(m => {
            if (m.info) {
                names[m.info.player1_name] = (names[m.info.player1_name] || 0) + 1
                names[m.info.player2_name] = (names[m.info.player2_name] || 0) + 1
            }
        })
        return Object.keys(names).reduce((a, b) => names[a] > names[b] ? a : b, 'Player')
    })

    const availableOpponents = computed(() => {
        const opponents = new Set()
        const main = mainPlayerName.value
        matches.value.forEach(m => {
            if (m.info) {
                if (m.info.player1_name !== main) opponents.add(m.info.player1_name)
                if (m.info.player2_name !== main) opponents.add(m.info.player2_name)
            }
        })
        return Array.from(opponents).sort()
    })

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
                // Strict check: One of the players must be the selected opponent
                const p1 = info.player1_name.toLowerCase()
                const p2 = info.player2_name.toLowerCase()
                if (p1 !== opp && p2 !== opp) {
                    return false
                }
            }

            // Filter CPU Matches
            if (filters.value.cpu) {
                const cpuPatterns = [/Incredible-/i, /Pro-/i, /Master-/i, /Junior-/i, /Club-/i, /-\d+$/]

                // If main player is identified, exclude matches where the OTHER player is CPU
                const main = mainPlayerName.value
                const opponentName = info.player1_name === main ? info.player2_name : info.player1_name

                if (cpuPatterns.some(p => p.test(opponentName))) return false
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

    // Helper to determine winner from score string
    function determineWinner(score) {
        if (!score) return null

        // Remove retirements/walkovers for parsing
        const cleanScore = score.replace(/\s*\(RET\)|\s*\(W\/O\)/i, '').trim()
        const sets = cleanScore.split(' ')

        let p1Sets = 0
        let p2Sets = 0

        sets.forEach(set => {
            // Handle super tiebreaks or normal sets
            if (set.includes('-')) {
                const [g1, g2] = set.split('-').map(v => parseInt(v))
                if (!isNaN(g1) && !isNaN(g2)) {
                    if (g1 > g2) p1Sets++
                    else if (g2 > g1) p2Sets++
                }
            }
        })

        if (p1Sets > p2Sets) return 'player1'
        if (p2Sets > p1Sets) return 'player2'
        return null // Draw or incomplete
    }

    // Comprehensive Aggregates
    const aggregateStats = computed(() => {
        const list = filteredMatches.value
        if (!list.length) return null

        // metrics to collect for Player 1 (User)
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

        // Metrics for Player 2 (Opponent) - for Comparison
        const oppMetrics = JSON.parse(JSON.stringify(metrics))

        // H2H & Win Rates
        let wins = 0
        let losses = 0
        let setsWon = 0
        let setsTotal = 0
        let gamesWon = 0
        let gamesTotal = 0

        list.forEach(m => {
            const p1 = m.player1
            const p2 = m.player2

            // Helper to push stats to metrics object
            const pushStats = (targetMetrics, p, otherP) => {
                if (p) {
                    // Serve
                    targetMetrics.first_serve_pct.push(p.serve.first_serve_pct)
                    targetMetrics.aces.push(p.serve.aces)
                    targetMetrics.double_faults.push(p.serve.double_faults)
                    if (p.serve.fastest_serve_kmh) targetMetrics.fastest_serve.push(p.serve.fastest_serve_kmh)
                    if (p.serve.avg_first_serve_kmh) targetMetrics.avg_first_serve.push(p.serve.avg_first_serve_kmh)
                    if (p.serve.avg_second_serve_kmh) targetMetrics.avg_second_serve.push(p.serve.avg_second_serve_kmh)
                    targetMetrics.first_serve_won_pct.push(p.points.points_on_first_serve_won / p.points.points_on_first_serve_total * 100 || 0)
                    targetMetrics.second_serve_won_pct.push(p.points.points_on_second_serve_won / p.points.points_on_second_serve_total * 100 || 0)

                    // Rally
                    if (p.rally.short_rallies_total > 0) targetMetrics.short_rally_won_pct.push(p.rally.short_rallies_won / p.rally.short_rallies_total * 100)
                    if (p.rally.normal_rallies_total > 0) targetMetrics.medium_rally_won_pct.push(p.rally.normal_rallies_won / p.rally.normal_rallies_total * 100)
                    if (p.rally.long_rallies_total > 0) targetMetrics.long_rally_won_pct.push(p.rally.long_rallies_won / p.rally.long_rallies_total * 100)
                    if (p.rally.avg_rally_length > 0) targetMetrics.avg_rally_length.push(p.rally.avg_rally_length)

                    // Points
                    targetMetrics.winners.push(p.points.winners)
                    targetMetrics.forced_errors.push(p.points.forced_errors)
                    targetMetrics.unforced_errors.push(p.points.unforced_errors)
                    if (p.points.net_points_total > 0) targetMetrics.net_points_won_pct.push(p.points.net_points_won / p.points.net_points_total * 100)
                    if (p.points.return_points_total > 0) targetMetrics.return_points_won_pct.push(p.points.return_points_won / p.points.return_points_total * 100)
                    targetMetrics.return_winners.push(p.points.return_winners)
                    targetMetrics.total_points_won_pct.push(p.points.total_points_won / (p.points.total_points_won + (otherP?.points?.total_points_won || 0)) * 100 || 0)

                    // Breaks
                    if (p.break_points.break_points_total > 0) targetMetrics.break_points_won_pct.push(p.break_points.break_points_won / p.break_points.break_points_total * 100)
                    if (p.break_points.break_games_total > 0) targetMetrics.break_games_won_pct.push(p.break_points.break_games_won / p.break_points.break_games_total * 100)
                    targetMetrics.set_points_saved.push(p.break_points.set_points_saved)
                    targetMetrics.match_points_saved.push(p.break_points.match_points_saved)
                }
            }

            // Collect Player 1 Stats
            pushStats(metrics, p1, p2)
            // Collect Player 2 Stats (for comparison)
            pushStats(oppMetrics, p2, p1)

            // Calculate Winner / H2H
            if (m.info && m.info.score) {
                const winner = determineWinner(m.info.score)
                if (winner === 'player1') wins++
                else if (winner === 'player2') losses++

                // Parse sets and games for percentages
                const cleanScore = m.info.score.replace(/\s*\(RET\)|\s*\(W\/O\)/i, '').trim()
                const sets = cleanScore.split(' ')
                sets.forEach(set => {
                    if (set.includes('-')) {
                        const [g1, g2] = set.split('-').map(v => parseInt(v))
                        if (!isNaN(g1) && !isNaN(g2)) {
                            gamesWon += g1
                            gamesTotal += (g1 + g2)
                            if (g1 > g2) setsWon++
                            setsTotal++
                        }
                    }
                })
            }
        })

        const calculateResults = (sourceMetrics) => {
            const result = {}
            const mode = statsMode.value

            Object.keys(sourceMetrics).forEach(key => {
                if (key === 'matches') return
                const values = sourceMetrics[key]
                if (values.length === 0) {
                    result[key] = 0
                    return
                }

                if (mode === 'avg') {
                    const sum = values.reduce((a, b) => a + b, 0)
                    result[key] = parseFloat((sum / values.length).toFixed(1))
                } else {
                    result[key] = parseFloat(calculateMedian(values).toFixed(1))
                }
            })
            return result
        }

        const p1Results = calculateResults(metrics)
        const p2Results = calculateResults(oppMetrics)

        p1Results.totalMatches = list.length

        // Add H2H and Win Rates to the result
        p1Results.wins = wins
        p1Results.losses = losses
        p1Results.win_pct = list.length > 0 ? (wins / list.length * 100).toFixed(1) : 0
        p1Results.set_win_pct = setsTotal > 0 ? (setsWon / setsTotal * 100).toFixed(1) : 0
        p1Results.game_win_pct = gamesTotal > 0 ? (gamesWon / gamesTotal * 100).toFixed(1) : 0

        // Attach opponent stats for comparison
        p1Results.opponent = p2Results

        return p1Results
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
        availableOpponents,
        mainPlayerName,
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
