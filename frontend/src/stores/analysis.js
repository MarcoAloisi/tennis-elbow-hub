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

            // Filter Unfinished Matches (Must have at least one set completed)
            // A completed set generally has at least 6 games for the winner or is a tiebreak (4-0 for Fast4? Assuming standard for now)
            // Score format examples: "6/3 6/2", "2/1" (incomplete), "7/6(4)"
            if (info.score) {
                // Quick check: if score is very short or doesn't look like a completed set
                // We'll trust the parser/regex to some extent, but let's look for at least one '6' or '7' or '4'(fast4)
                // Better approach: Parse the first set.
                const cleanScore = info.score.replace(/\s*\(RET\)|\s*\(W\/O\)/i, '').trim()
                const sets = cleanScore.split(' ')
                if (sets.length === 0) return false

                const firstSet = sets[0]
                const separator = firstSet.includes('/') ? '/' : '-'
                if (firstSet.includes(separator)) {
                    const [g1, g2] = firstSet.split(separator).map(v => parseInt(v))

                    // Filter matches where no set was completed
                    // A "complete set" requires at least one player to reach 6 games (standard) or 4 (fast4)
                    // Matches like "2/1" or "3/0" are clearly incomplete
                    if (!isNaN(g1) && !isNaN(g2)) {
                        // STRICTER CHECK: At least one player must have reached 4 games
                        // This covers Standard (6-X) and Fast4 (4-X)
                        // Filters out "2/1", "3/2", "1/0" etc.
                        if (g1 < 4 && g2 < 4) return false
                    }
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
            const separator = set.includes('/') ? '/' : '-'
            if (set.includes(separator)) {
                const [g1, g2] = set.split(separator).map(v => parseInt(v))
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

        // metrics to collect for Player 1 (User) - Now storing SUMS for accurate weighted averages
        const metrics = {
            matches: 0,

            // Serve
            first_serve_in: 0,
            first_serve_total: 0,
            aces: 0,
            double_faults: 0,
            fastest_serve_max: 0,
            avg_first_serve_sum: 0,
            avg_first_serve_count: 0,
            avg_second_serve_sum: 0,
            avg_second_serve_count: 0,

            points_on_first_serve_won: 0,
            points_on_first_serve_total: 0,
            points_on_second_serve_won: 0,
            points_on_second_serve_total: 0,

            // Rally
            short_rallies_won: 0,
            short_rallies_total: 0,
            normal_rallies_won: 0,
            normal_rallies_total: 0,
            long_rallies_won: 0,
            long_rallies_total: 0,
            avg_rally_length_sum: 0,
            avg_rally_length_count: 0,

            // Points
            winners: 0,
            forced_errors: 0,
            unforced_errors: 0,
            net_points_won: 0,
            net_points_total: 0,
            return_points_won: 0,
            return_points_total: 0,
            return_winners: 0,
            total_points_won: 0,
            total_points_played: 0,

            // Breaks
            break_points_won: 0,
            break_points_total: 0,
            break_games_won: 0,
            break_games_total: 0,
            set_points_saved: 0,
            match_points_saved: 0
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

        // Determine the "Main Player" (The User)
        // If opponent filter is active, User is the player NOT matching the opponent name
        let currentUser = mainPlayerName.value

        list.forEach(m => {
            if (!m.info) return

            let userP, oppP
            let isUserP1 = true

            // Refined User Detection Logic
            if (filters.value.opponent) {
                // In H2H mode, if P1 is the opponent, then P2 is the User
                if (m.info.player1_name.toLowerCase() === filters.value.opponent.toLowerCase()) {
                    userP = m.player2
                    oppP = m.player1
                    isUserP1 = false
                    // Update currentUser for consistency if not already set correctly
                    currentUser = m.info.player2_name
                } else if (m.info.player2_name.toLowerCase() === filters.value.opponent.toLowerCase()) {
                    userP = m.player1
                    oppP = m.player2
                    isUserP1 = true
                } else {
                    // Neither matches filter (shouldn't happen due to filter logic), fallback to default
                    if (m.info.player1_name === currentUser) {
                        userP = m.player1
                        oppP = m.player2
                        isUserP1 = true
                    } else {
                        userP = m.player2
                        oppP = m.player1
                        isUserP1 = false
                    }
                }
            } else {
                // Global mode
                if (m.info.player1_name === currentUser) {
                    userP = m.player1
                    oppP = m.player2
                    isUserP1 = true
                } else {
                    userP = m.player2
                    oppP = m.player1
                    isUserP1 = false
                }
            }

            // Collection Stats for User
            const pushStats = (targetMetrics, p, otherP) => {
                if (p) {
                    targetMetrics.matches++

                    // Serve
                    targetMetrics.first_serve_in += parseFloat(p.serve.first_serve_in || 0)
                    targetMetrics.first_serve_total += parseFloat(p.serve.first_serve_total || 0)
                    targetMetrics.aces += parseFloat(p.serve.aces || 0)
                    targetMetrics.double_faults += parseFloat(p.serve.double_faults || 0)

                    if (p.serve.fastest_serve_kmh > targetMetrics.fastest_serve_max) {
                        targetMetrics.fastest_serve_max = p.serve.fastest_serve_kmh
                    }
                    if (p.serve.avg_first_serve_kmh > 0) {
                        targetMetrics.avg_first_serve_sum += p.serve.avg_first_serve_kmh
                        targetMetrics.avg_first_serve_count++
                    }
                    if (p.serve.avg_second_serve_kmh > 0) {
                        targetMetrics.avg_second_serve_sum += p.serve.avg_second_serve_kmh
                        targetMetrics.avg_second_serve_count++
                    }

                    targetMetrics.points_on_first_serve_won += parseFloat(p.points.points_on_first_serve_won || 0)
                    targetMetrics.points_on_first_serve_total += parseFloat(p.points.points_on_first_serve_total || 0)
                    targetMetrics.points_on_second_serve_won += parseFloat(p.points.points_on_second_serve_won || 0)
                    targetMetrics.points_on_second_serve_total += parseFloat(p.points.points_on_second_serve_total || 0)

                    // Rally
                    targetMetrics.short_rallies_won += parseFloat(p.rally.short_rallies_won || 0)
                    targetMetrics.short_rallies_total += parseFloat(p.rally.short_rallies_total || 0)
                    targetMetrics.normal_rallies_won += parseFloat(p.rally.normal_rallies_won || 0)
                    targetMetrics.normal_rallies_total += parseFloat(p.rally.normal_rallies_total || 0)
                    targetMetrics.long_rallies_won += parseFloat(p.rally.long_rallies_won || 0)
                    targetMetrics.long_rallies_total += parseFloat(p.rally.long_rallies_total || 0)

                    if (p.rally.avg_rally_length > 0) {
                        targetMetrics.avg_rally_length_sum += p.rally.avg_rally_length
                        targetMetrics.avg_rally_length_count++
                    }

                    // Points
                    targetMetrics.winners += parseFloat(p.points.winners || 0)
                    targetMetrics.forced_errors += parseFloat(p.points.forced_errors || 0)
                    targetMetrics.unforced_errors += parseFloat(p.points.unforced_errors || 0)

                    targetMetrics.net_points_won += parseFloat(p.points.net_points_won || 0)
                    targetMetrics.net_points_total += parseFloat(p.points.net_points_total || 0)

                    targetMetrics.return_points_won += parseFloat(p.points.return_points_won || 0)
                    targetMetrics.return_points_total += parseFloat(p.points.return_points_total || 0)
                    targetMetrics.return_winners += parseFloat(p.points.return_winners || 0)

                    targetMetrics.total_points_won += parseFloat(p.points.total_points_won || 0)
                    targetMetrics.total_points_played += (parseFloat(p.points.total_points_won || 0) + parseFloat(otherP?.points?.total_points_won || 0))

                    // Breaks
                    targetMetrics.break_points_won += parseFloat(p.break_points.break_points_won || 0)
                    targetMetrics.break_points_total += parseFloat(p.break_points.break_points_total || 0)
                    targetMetrics.break_games_won += parseFloat(p.break_points.break_games_won || 0)
                    targetMetrics.break_games_total += parseFloat(p.break_points.break_games_total || 0)

                    targetMetrics.set_points_saved += parseFloat(p.break_points.set_points_saved || 0)
                    targetMetrics.match_points_saved += parseFloat(p.break_points.match_points_saved || 0)
                }
            }

            // Collect User Stats 
            pushStats(metrics, userP, oppP)
            // Collect Opponent Stats
            pushStats(oppMetrics, oppP, userP)

            // Calculate Winner / H2H
            if (m.info && m.info.score) {
                const winner = determineWinner(m.info.score)
                const userWon = (winner === 'player1' && isUserP1) || (winner === 'player2' && !isUserP1)

                if (userWon) wins++
                else if (winner) losses++

                const cleanScore = m.info.score.replace(/\s*\(RET\)|\s*\(W\/O\)/i, '').trim()
                const sets = cleanScore.split(' ')
                sets.forEach(set => {
                    const separator = set.includes('/') ? '/' : '-'
                    if (set.includes(separator)) {
                        const [g1, g2] = set.split(separator).map(v => parseInt(v))
                        if (!isNaN(g1) && !isNaN(g2)) {
                            const userGames = isUserP1 ? g1 : g2
                            const oppGames = isUserP1 ? g2 : g1

                            gamesWon += userGames
                            gamesTotal += (userGames + oppGames)

                            if (userGames > oppGames) setsWon++
                            setsTotal++
                        }
                    }
                })
            }
        })

        // Helper to finalize weighted averages
        const calculateFinals = (m) => {
            const count = m.matches || 1
            const safeDiv = (n, d) => d > 0 ? (n / d) * 100 : 0

            return {
                // Serve
                first_serve_pct: safeDiv(m.first_serve_in, m.first_serve_total),
                first_serve_in: m.first_serve_in,
                first_serve_total: m.first_serve_total,

                aces: parseFloat((m.aces / count).toFixed(1)), // Avg per match
                double_faults: parseFloat((m.double_faults / count).toFixed(1)), // Avg per match

                fastest_serve_kmh: m.fastest_serve_max,
                avg_first_serve_kmh: m.avg_first_serve_count > 0 ? m.avg_first_serve_sum / m.avg_first_serve_count : 0,
                avg_second_serve_kmh: m.avg_second_serve_count > 0 ? m.avg_second_serve_sum / m.avg_second_serve_count : 0,

                first_serve_won_pct: safeDiv(m.points_on_first_serve_won, m.points_on_first_serve_total),
                points_on_first_serve_won: m.points_on_first_serve_won,
                points_on_first_serve_total: m.points_on_first_serve_total,

                second_serve_won_pct: safeDiv(m.points_on_second_serve_won, m.points_on_second_serve_total),
                points_on_second_serve_won: m.points_on_second_serve_won,
                points_on_second_serve_total: m.points_on_second_serve_total,

                // Rally
                short_rally_won_pct: safeDiv(m.short_rallies_won, m.short_rallies_total),
                medium_rally_won_pct: safeDiv(m.normal_rallies_won, m.normal_rallies_total),
                long_rally_won_pct: safeDiv(m.long_rallies_won, m.long_rallies_total),
                avg_rally_length: m.avg_rally_length_count > 0 ? parseFloat((m.avg_rally_length_sum / m.avg_rally_length_count).toFixed(1)) : 0,

                // Points
                winners: parseFloat((m.winners / count).toFixed(1)),
                forced_errors: parseFloat((m.forced_errors / count).toFixed(1)),
                unforced_errors: parseFloat((m.unforced_errors / count).toFixed(1)),

                net_points_won_pct: safeDiv(m.net_points_won, m.net_points_total),
                net_points_won: m.net_points_won,
                net_points_total: m.net_points_total,

                return_points_won_pct: safeDiv(m.return_points_won, m.return_points_total),
                return_points_won: m.return_points_won,
                return_points_total: m.return_points_total,

                return_winners: parseFloat((m.return_winners / count).toFixed(1)),

                total_points_won_pct: safeDiv(m.total_points_won, m.total_points_played),
                total_points_won: m.total_points_won,

                // Breaks - Store raw for "3/8 (37%)" format
                break_points_won_pct: safeDiv(m.break_points_won, m.break_points_total),
                break_points_won: m.break_points_won,
                break_points_total: m.break_points_total,

                break_games_won_pct: safeDiv(m.break_games_won, m.break_games_total),
                break_games_won: m.break_games_won,
                break_games_total: m.break_games_total,

                set_points_saved: parseFloat((m.set_points_saved / count).toFixed(1)),
                match_points_saved: parseFloat((m.match_points_saved / count).toFixed(1))
            }
        }

        const p1Results = calculateFinals(metrics)
        const p2Results = calculateFinals(oppMetrics)

        p1Results.totalMatches = list.length
        p1Results.wins = wins
        p1Results.losses = losses
        p1Results.win_pct = list.length > 0 ? (wins / list.length * 100).toFixed(1) : 0
        p1Results.set_win_pct = setsTotal > 0 ? (setsWon / setsTotal * 100).toFixed(1) : 0
        p1Results.game_win_pct = gamesTotal > 0 ? (gamesWon / gamesTotal * 100).toFixed(1) : 0

        // Attach opponent stats
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
