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
    const userAliases = ref([]) // List of names user identified as themselves

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
    const isIdentityConfirmed = computed(() => userAliases.value.length > 0 && hasMatches.value)

    const allPlayerNames = computed(() => {
        if (!matches.value.length) return []
        const counts = {}
        matches.value.forEach(m => {
            if (m.info) {
                counts[m.info.player1_name] = (counts[m.info.player1_name] || 0) + 1
                counts[m.info.player2_name] = (counts[m.info.player2_name] || 0) + 1
            }
        })
        return Object.entries(counts).map(([name, count]) => ({ name, count }))
    })

    // Determining User Identity (Auto or Manual)
    // We prefer manual userAliases if set, otherwise fallback to most frequent
    const mainPlayerName = computed(() => {
        if (userAliases.value.length > 0) return userAliases.value[0] // Primary alias

        // Fallback Auto-Detect (same as before)
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

    // Available opponents should exclude any of the user's aliases
    const availableOpponents = computed(() => {
        const opponents = new Set()
        matches.value.forEach(m => {
            if (m.info) {
                // Should exclude any name in userAliases
                if (userAliases.value.length > 0) {
                    if (!userAliases.value.includes(m.info.player1_name)) opponents.add(m.info.player1_name)
                    if (!userAliases.value.includes(m.info.player2_name)) opponents.add(m.info.player2_name)
                } else {
                    // Fallback if no aliases set
                    const main = mainPlayerName.value
                    if (m.info.player1_name !== main) opponents.add(m.info.player1_name)
                    if (m.info.player2_name !== main) opponents.add(m.info.player2_name)
                }
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

                // Identify if opponent is CPU
                let opponentName = ''
                if (userAliases.value.length > 0) {
                    if (userAliases.value.includes(info.player1_name)) {
                        opponentName = info.player2_name
                    } else if (userAliases.value.includes(info.player2_name)) {
                        opponentName = info.player1_name
                    } else {
                        // Fallback logic
                        opponentName = info.player1_name // Assume P1 if neither match (weird case)
                    }
                } else {
                    const main = mainPlayerName.value
                    opponentName = info.player1_name === main ? info.player2_name : info.player1_name
                }

                if (cpuPatterns.some(p => p.test(opponentName))) return false
            }

            // Filter by Surface (Tournament name check)
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

            // Filter Unfinished Matches
            if (info.score) {
                const cleanScore = info.score.replace(/\s*\(RET\)|\s*\(W\/O\)/i, '').trim()
                const sets = cleanScore.split(' ')
                if (sets.length === 0) return false

                const firstSet = sets[0]
                const separator = firstSet.includes('/') ? '/' : '-'
                if (firstSet.includes(separator)) {
                    const [g1, g2] = firstSet.split(separator).map(v => parseInt(v))
                    // STRICTER CHECK: At least one player must have reached 4 games
                    if (!isNaN(g1) && !isNaN(g2)) {
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
        const cleanScore = score.replace(/\s*\(RET\)|\s*\(W\/O\)/i, '').trim()
        const sets = cleanScore.split(' ')

        let p1Sets = 0
        let p2Sets = 0

        sets.forEach(set => {
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
        return null
    }

    // Comprehensive Aggregates
    const aggregateStats = computed(() => {
        const list = filteredMatches.value
        if (!list.length) return null

        // Initialize collections for Median/Avg calculation
        // We act like we are collecting for "Main Player" vs "Opponent"
        const collections = {
            p1: {},
            p2: {}
        }

        // Structure for metrics we want to track
        const metricKeys = [
            'first_serve_in', 'first_serve_total', 'first_serve_pct',
            'aces', 'double_faults',
            'fastest_serve_kmh', 'avg_first_serve_kmh', 'avg_second_serve_kmh',
            'points_on_first_serve_won', 'points_on_first_serve_total', 'first_serve_won_pct',
            'points_on_second_serve_won', 'points_on_second_serve_total', 'second_serve_won_pct',
            'short_rallies_won', 'short_rallies_total', 'short_rallies_pct',
            'normal_rallies_won', 'normal_rallies_total', 'normal_rallies_pct',
            'long_rallies_won', 'long_rallies_total', 'long_rallies_pct',
            'avg_rally_length',
            'winners', 'forced_errors', 'unforced_errors',
            'net_points_won', 'net_points_total', 'net_points_won_pct',
            'return_points_won', 'return_points_total', 'return_points_won_pct',
            'return_winners',
            'total_points_won', 'total_points_played', 'total_points_won_pct',
            'break_points_won', 'break_points_total', 'break_points_won_pct',
            'break_games_won', 'break_games_total', 'break_games_won_pct',
            'set_points_saved', 'match_points_saved',
            // New match-level distributions
            'match_set_win_pct', 'match_game_win_pct'
        ];


        // Initialize arrays
        ['p1', 'p2'].forEach(pKey => {
            metricKeys.forEach(k => collections[pKey][k] = [])
        })

        // H2H & Win Rates
        let wins = 0
        let losses = 0
        let setsWon = 0
        let setsTotal = 0
        let gamesWon = 0
        let gamesTotal = 0

        // Determine user identity for this specific aggregation
        const currentIdentity = userAliases.value.length > 0 ? userAliases.value : [mainPlayerName.value]

        list.forEach(m => {
            if (!m.info) return

            let userP, oppP
            let isUserP1 = true

            // Logic: Is P1 in our aliases?
            if (currentIdentity.includes(m.info.player1_name)) {
                isUserP1 = true
                userP = m.player1
                oppP = m.player2
            }
            // Is P2 in our aliases?
            else if (currentIdentity.includes(m.info.player2_name)) {
                isUserP1 = false
                userP = m.player2
                oppP = m.player1
            }
            // Neither?
            else {
                // If filters.opponent is set, assume the OTHER player is the user
                if (filters.value.opponent) {
                    if (m.info.player1_name.toLowerCase() === filters.value.opponent.toLowerCase()) {
                        userP = m.player2
                        oppP = m.player1
                        isUserP1 = false
                    } else {
                        userP = m.player1
                        oppP = m.player2
                        isUserP1 = true
                    }
                } else {
                    // Default fallback
                    isUserP1 = true
                    userP = m.player1
                    oppP = m.player2
                }
            }

            // --- Helper to extract values ---
            const pushMetric = (targetObj, p, otherP) => {
                if (!p) return

                // Helper to push raw value or calculated percent
                const push = (key, val) => targetObj[key].push(parseFloat(val || 0))
                const pushPct = (key, n, d) => targetObj[key].push(d > 0 ? (n / d) * 100 : 0)

                // Serve
                push('first_serve_in', p.serve.first_serve_in)
                push('first_serve_total', p.serve.first_serve_total)
                pushPct('first_serve_pct', p.serve.first_serve_in, p.serve.first_serve_total)

                push('aces', p.serve.aces)
                push('double_faults', p.serve.double_faults)
                push('fastest_serve_kmh', p.serve.fastest_serve_kmh)
                push('avg_first_serve_kmh', p.serve.avg_first_serve_kmh)
                push('avg_second_serve_kmh', p.serve.avg_second_serve_kmh)

                // Points on Serve
                push('points_on_first_serve_won', p.points.points_on_first_serve_won)
                push('points_on_first_serve_total', p.points.points_on_first_serve_total)
                pushPct('first_serve_won_pct', p.points.points_on_first_serve_won, p.points.points_on_first_serve_total)

                push('points_on_second_serve_won', p.points.points_on_second_serve_won)
                push('points_on_second_serve_total', p.points.points_on_second_serve_total)
                pushPct('second_serve_won_pct', p.points.points_on_second_serve_won, p.points.points_on_second_serve_total)

                // Rally
                push('short_rallies_won', p.rally.short_rallies_won)
                push('short_rallies_total', p.rally.short_rallies_total)
                pushPct('short_rallies_pct', p.rally.short_rallies_won, p.rally.short_rallies_total)

                push('normal_rallies_won', p.rally.normal_rallies_won)
                push('normal_rallies_total', p.rally.normal_rallies_total)
                pushPct('normal_rallies_pct', p.rally.normal_rallies_won, p.rally.normal_rallies_total)

                push('long_rallies_won', p.rally.long_rallies_won)
                push('long_rallies_total', p.rally.long_rallies_total)
                pushPct('long_rallies_pct', p.rally.long_rallies_won, p.rally.long_rallies_total)

                push('avg_rally_length', p.rally.avg_rally_length)

                // Points
                push('winners', p.points.winners)
                push('forced_errors', p.points.forced_errors)
                push('unforced_errors', p.points.unforced_errors)

                push('net_points_won', p.points.net_points_won)
                push('net_points_total', p.points.net_points_total)
                pushPct('net_points_won_pct', p.points.net_points_won, p.points.net_points_total)

                push('return_points_won', p.points.return_points_won)
                push('return_points_total', p.points.return_points_total)
                pushPct('return_points_won_pct', p.points.return_points_won, p.points.return_points_total)

                push('return_winners', p.points.return_winners)

                const totalPlayed = (p.points.total_points_won || 0) + (otherP?.points?.total_points_won || 0)
                push('total_points_won', p.points.total_points_won)
                push('total_points_played', totalPlayed)
                pushPct('total_points_won_pct', p.points.total_points_won, totalPlayed)

                // Breaks
                push('break_points_won', p.break_points.break_points_won)
                push('break_points_total', p.break_points.break_points_total)
                pushPct('break_points_won_pct', p.break_points.break_points_won, p.break_points.break_points_total)

                push('break_games_won', p.break_points.break_games_won)
                push('break_games_total', p.break_points.break_games_total)
                pushPct('break_games_won_pct', p.break_points.break_games_won, p.break_points.break_games_total)

                push('set_points_saved', p.break_points.set_points_saved)
                push('match_points_saved', p.break_points.match_points_saved)
            }

            pushMetric(collections.p1, userP, oppP)
            pushMetric(collections.p2, oppP, userP)

            // Calculate Winner / H2H & Match Distributions
            if (m.info && m.info.score) {
                const winner = determineWinner(m.info.score)
                const userWon = (winner === 'player1' && isUserP1) || (winner === 'player2' && !isUserP1)

                if (userWon) wins++
                else if (winner) losses++

                const cleanScore = m.info.score.replace(/\s*\(RET\)|\s*\(W\/O\)/i, '').trim()
                const sets = cleanScore.split(' ')

                let mUserGames = 0
                let mOppGames = 0
                let mUserSets = 0
                let mOppSets = 0

                sets.forEach(set => {
                    const separator = set.includes('/') ? '/' : '-'
                    if (set.includes(separator)) {
                        const [g1, g2] = set.split(separator).map(v => parseInt(v))
                        if (!isNaN(g1) && !isNaN(g2)) {
                            const userG = isUserP1 ? g1 : g2
                            const oppG = isUserP1 ? g2 : g1

                            mUserGames += userG
                            mOppGames += oppG

                            gamesWon += userG
                            gamesTotal += (userG + oppG)

                            if (userG > oppG) {
                                setsWon++
                                mUserSets++
                            } else if (oppG > userG) {
                                mOppSets++
                            }
                            setsTotal++
                        }
                    }
                })

                // Push percentages for this match
                const safePct = (n, d) => d > 0 ? (n / d) * 100 : 0
                const mTotalGames = mUserGames + mOppGames
                const mTotalSets = mUserSets + mOppSets

                collections.p1['match_game_win_pct'].push(safePct(mUserGames, mTotalGames))
                collections.p1['match_set_win_pct'].push(safePct(mUserSets, mTotalSets))

                collections.p2['match_game_win_pct'].push(safePct(mOppGames, mTotalGames))
                collections.p2['match_set_win_pct'].push(safePct(mOppSets, mTotalSets))
            }
        })

        // --- Aggregation Helper ---
        const computeFinals = (metrics) => {
            const result = {}
            const isMedian = statsMode.value === 'median'

            const getVal = (key) => {
                const arr = metrics[key]
                if (!arr || !arr.length) return 0
                if (isMedian) return calculateMedian(arr)
                // Default Average
                const sum = arr.reduce((a, b) => a + b, 0)
                return sum / arr.length
            }

            const sum = (key) => {
                const arr = metrics[key] || []
                return arr.reduce((a, b) => a + b, 0)
            }

            // Helper for Percentage Fields: Weighted Average vs Median of Matches
            const getPct = (key, numKey, denomKey) => {
                if (isMedian) {
                    // In Median mode, return the median of the percent array
                    // Special keys for games/sets
                    if (key === 'game_win_pct') return getVal('match_game_win_pct')
                    if (key === 'set_win_pct') return getVal('match_set_win_pct')

                    // For other stats (like 1st Serve %), we need to have collected the per-match percentages
                    // Our pushMetric function already collected 'first_serve_pct' array!
                    // So we can just use getVal(key) for Median.
                    return getVal(key)
                }

                // In Average mode, use Weighted Average (Sum(Num) / Sum(Denom))
                if (key === 'game_win_pct') return gamesTotal > 0 ? (gamesWon / gamesTotal * 100) : 0
                if (key === 'set_win_pct') return setsTotal > 0 ? (setsWon / setsTotal * 100) : 0

                // Standard stats
                const num = sum(numKey)
                const denom = sum(denomKey)
                return denom > 0 ? (num / denom * 100) : 0
            }

            // Mappings

            // Serve
            result.first_serve_in = sum('first_serve_in')
            result.first_serve_total = sum('first_serve_total')
            result.first_serve_pct = getPct('first_serve_pct', 'first_serve_in', 'first_serve_total')

            result.aces = getVal('aces').toFixed(1)
            result.double_faults = getVal('double_faults').toFixed(1)

            result.fastest_serve_kmh = Math.max(...(metrics['fastest_serve_kmh'] || [0]))
            result.avg_first_serve_kmh = getVal('avg_first_serve_kmh')
            result.avg_second_serve_kmh = getVal('avg_second_serve_kmh')

            // Points on Serve
            result.points_on_first_serve_won = sum('points_on_first_serve_won')
            result.points_on_first_serve_total = sum('points_on_first_serve_total')
            result.first_serve_won_pct = getPct('first_serve_won_pct', 'points_on_first_serve_won', 'points_on_first_serve_total')

            result.points_on_second_serve_won = sum('points_on_second_serve_won')
            result.points_on_second_serve_total = sum('points_on_second_serve_total')
            result.second_serve_won_pct = getPct('second_serve_won_pct', 'points_on_second_serve_won', 'points_on_second_serve_total')

            // Rally
            result.short_rallies_won = sum('short_rallies_won')
            result.short_rallies_total = sum('short_rallies_total')
            result.short_rally_won_pct = getPct('short_rallies_pct', 'short_rallies_won', 'short_rallies_total')

            result.normal_rallies_won = sum('normal_rallies_won')
            result.normal_rallies_total = sum('normal_rallies_total')
            result.medium_rally_won_pct = getPct('normal_rallies_pct', 'normal_rallies_won', 'normal_rallies_total')

            result.long_rallies_won = sum('long_rallies_won')
            result.long_rallies_total = sum('long_rallies_total')
            result.long_rally_won_pct = getPct('long_rallies_pct', 'long_rallies_won', 'long_rallies_total')

            result.avg_rally_length = getVal('avg_rally_length').toFixed(1)

            // Points
            result.winners = getVal('winners').toFixed(1)
            result.forced_errors = getVal('forced_errors').toFixed(1)
            result.unforced_errors = getVal('unforced_errors').toFixed(1)

            result.net_points_won = sum('net_points_won')
            result.net_points_total = sum('net_points_total')
            result.net_points_won_pct = getPct('net_points_won_pct', 'net_points_won', 'net_points_total')

            result.return_points_won = sum('return_points_won')
            result.return_points_total = sum('return_points_total')
            result.return_points_won_pct = getPct('return_points_won_pct', 'return_points_won', 'return_points_total')

            result.return_winners = getVal('return_winners').toFixed(1)

            result.total_points_won = sum('total_points_won')
            const totalPlayed = sum('total_points_played')
            result.total_points_played = totalPlayed // for reference
            result.total_points_won_pct = getPct('total_points_won_pct', 'total_points_won', 'total_points_played')

            // Breaks
            result.break_points_won = sum('break_points_won')
            result.break_points_total = sum('break_points_total')
            result.break_points_won_pct = getPct('break_points_won_pct', 'break_points_won', 'break_points_total')

            result.break_games_won = sum('break_games_won')
            result.break_games_total = sum('break_games_total')
            result.break_games_won_pct = getPct('break_games_won_pct', 'break_games_won', 'break_games_total')

            result.set_points_saved = getVal('set_points_saved').toFixed(1)
            result.match_points_saved = getVal('match_points_saved').toFixed(1)

            // Win Rates (Special handling for Median)
            result.win_pct = (list.length > 0 ? (wins / list.length * 100) : 0).toFixed(1) // Always global average
            result.game_win_pct = getPct('game_win_pct', null, null).toFixed(1)
            result.set_win_pct = getPct('set_win_pct', null, null).toFixed(1)

            return result
        }

        const p1Results = computeFinals(collections.p1)
        const p2Results = computeFinals(collections.p2)

        p1Results.totalMatches = list.length
        p1Results.wins = wins
        p1Results.losses = losses
        // win_pct, set_win_pct, game_win_pct are now calculated inside computeFinals and assigned to p1Results

        p1Results.opponent = p2Results
        return p1Results
    })

    // Actions
    async function uploadAndAnalyze(file) {
        isLoading.value = true
        error.value = null
        uploadProgress.value = 0
        userAliases.value = [] // Reset aliases on new upload

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

    function setIdentifiedPlayers(aliases) {
        userAliases.value = aliases
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
        userAliases.value = []
        error.value = null
    }

    function selectMatch(index) {
        if (index >= 0 && index < matches.value.length) {
            currentMatchIndex.value = index
        }
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
        userAliases,
        // Getters
        hasMatches,
        isIdentityConfirmed,
        allPlayerNames,
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
        setIdentifiedPlayers,
        loadSampleAnalysis,
        clearAnalysis,
        selectMatch,
        setFilter,
        clearFilters
    }
})
