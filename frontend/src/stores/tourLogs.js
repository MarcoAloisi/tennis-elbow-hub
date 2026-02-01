/**
 * Tour Logs Pinia Store
 * 
 * Manages WTSL tour logs data, filtering, and computed statistics.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL || ''

export const useTourLogsStore = defineStore('tourLogs', () => {
    // State
    const rawData = ref([])
    const isLoading = ref(false)
    const error = ref(null)

    // Filters
    const filters = ref({
        player: '',
        tournament: '',
        dateStart: '',
        dateEnd: '',
    })

    // Active subtab
    const activeTab = ref('data') // 'data', 'rankings', 'leaders'

    // Fetch data from API
    async function fetchData() {
        isLoading.value = true
        error.value = null

        try {
            const response = await fetch(`${API_BASE}/api/tour-logs`)
            if (!response.ok) {
                throw new Error('Failed to fetch tour logs')
            }
            const result = await response.json()
            rawData.value = result.data || []
        } catch (e) {
            error.value = e.message
            console.error('Tour logs fetch error:', e)
        } finally {
            isLoading.value = false
        }
    }

    // Normalize tournament name - remove time suffixes like "Day/Night" and typos
    function normalizeTournament(name) {
        if (!name) return ''
        // Remove common suffixes
        let normalized = name
            .replace(/\s+(Day|Night|Session\s*\d*)$/i, '')
            .replace(/\s+\d{1,2}:\d{2}.*$/, '') // Remove time stamps
            .replace(/_/g, ' ')
            .trim()
        return normalized
    }

    // Normalize player name for consistent matching (preserve original casing for display)
    function normalizePlayerKey(name) {
        if (!name) return ''
        return name.toLowerCase().trim()
    }

    // Create unique match key to deduplicate (case-insensitive)
    function createMatchKey(row) {
        // Sort players alphabetically (case-insensitive) to ensure same match from both perspectives has same key
        const players = [normalizePlayerKey(row.player), normalizePlayerKey(row.opponent)].sort()
        return `${row.date}|${players[0]}|${players[1]}|${row.result}`
    }

    // Deduplicated data - keep only the WINNER's row (player with ELO +X)
    // Each match has 2 rows (one per player), we only want the winner's perspective
    const data = computed(() => {
        const unique = []

        for (const row of rawData.value) {
            // Only keep rows where the player WON (ELO +X)
            if (row.playerWon !== true) continue

            unique.push({
                ...row,
                // Normalize player names for consistent display
                playerNormalized: normalizePlayerKey(row.player),
                opponentNormalized: normalizePlayerKey(row.opponent),
                tournamentNormalized: normalizeTournament(row.tournament)
            })
        }

        return unique
    })

    // Get unique players for autocomplete (case-insensitive, keep best display name)
    const uniquePlayers = computed(() => {
        const playerMap = new Map() // key -> display name (first seen)
        data.value.forEach(row => {
            if (row.player) {
                const key = row.playerNormalized
                if (!playerMap.has(key)) playerMap.set(key, row.player)
            }
            if (row.opponent) {
                const key = row.opponentNormalized
                if (!playerMap.has(key)) playerMap.set(key, row.opponent)
            }
        })
        return Array.from(playerMap.values()).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }))
    })

    // Get unique normalized tournaments
    const uniqueTournaments = computed(() => {
        const tournaments = new Set()
        data.value.forEach(row => {
            if (row.tournamentNormalized) tournaments.add(row.tournamentNormalized)
        })
        return Array.from(tournaments).sort()
    })

    // Player suggestions based on filter input
    const playerSuggestions = computed(() => {
        if (!filters.value.player || filters.value.player.length < 1) return []
        const search = filters.value.player.toLowerCase()
        return uniquePlayers.value
            .filter(p => p.toLowerCase().includes(search))
            .slice(0, 10)
    })

    // Parse date string DD/MM/YYYY to Date object
    function parseDate(dateStr) {
        if (!dateStr) return null
        const [day, month, year] = dateStr.split('/')
        return new Date(year, month - 1, day)
    }

    // Filtered data based on current filters
    const filteredData = computed(() => {
        return data.value.filter(row => {
            // Player filter (search in both player and opponent)
            if (filters.value.player) {
                const search = filters.value.player.toLowerCase()
                const matchPlayer = row.player?.toLowerCase().includes(search)
                const matchOpponent = row.opponent?.toLowerCase().includes(search)
                if (!matchPlayer && !matchOpponent) return false
            }

            // Tournament filter (use normalized name)
            if (filters.value.tournament && row.tournamentNormalized !== filters.value.tournament) {
                return false
            }

            // Date range filter
            if (filters.value.dateStart || filters.value.dateEnd) {
                const rowDate = parseDate(row.date)
                if (!rowDate) return false

                if (filters.value.dateStart) {
                    const startDate = new Date(filters.value.dateStart)
                    if (rowDate < startDate) return false
                }
                if (filters.value.dateEnd) {
                    const endDate = new Date(filters.value.dateEnd)
                    if (rowDate > endDate) return false
                }
            }

            return true
        })
    })

    // Helper: Calculate average
    function average(values) {
        const valid = values.filter(v => v !== null && v !== undefined && !isNaN(v))
        if (valid.length === 0) return null
        return valid.reduce((a, b) => a + b, 0) / valid.length
    }

    // Player rankings (win% and ELO) - case-insensitive grouping
    // Now that data only contains winner rows: player = winner, opponent = loser
    const playerRankings = computed(() => {
        const stats = {} // keyed by normalized name

        filteredData.value.forEach(row => {
            // Player column = winner of this match
            if (row.player) {
                const key = row.playerNormalized
                if (!stats[key]) {
                    stats[key] = { displayName: row.player, wins: 0, losses: 0, elo: null, lastDate: null }
                }
                stats[key].wins++

                // Update ELO if this is a more recent match
                const rowDate = parseDate(row.date)
                if (row.elo !== null && (!stats[key].lastDate || rowDate > stats[key].lastDate)) {
                    stats[key].elo = row.elo
                    stats[key].lastDate = rowDate
                }
            }

            // Opponent column = loser of this match
            if (row.opponent) {
                const key = row.opponentNormalized
                if (!stats[key]) {
                    stats[key] = { displayName: row.opponent, wins: 0, losses: 0, elo: null, lastDate: null }
                }
                stats[key].losses++

                // Update ELO if more recent
                const rowDate = parseDate(row.date)
                if (row.opponentElo !== null && (!stats[key].lastDate || rowDate > stats[key].lastDate)) {
                    stats[key].elo = row.opponentElo
                    stats[key].lastDate = rowDate
                }
            }
        })

        // Calculate win% and create ranking array (minimum 5 matches)
        return Object.entries(stats)
            .map(([key, s]) => ({
                name: s.displayName,
                wins: s.wins,
                losses: s.losses,
                matches: s.wins + s.losses,
                winPct: s.wins + s.losses > 0
                    ? (s.wins / (s.wins + s.losses) * 100).toFixed(1)
                    : 0,
                elo: s.elo,
            }))
            .filter(p => p.matches >= 5)
            .sort((a, b) => {
                // Sort by win% desc, then by matches desc
                const winDiff = parseFloat(b.winPct) - parseFloat(a.winPct)
                return winDiff !== 0 ? winDiff : b.matches - a.matches
            })
    })

    // Stats leaders - average stats per player (using only winner stats from each match)
    const statsLeaders = computed(() => {
        const playerStats = {} // keyed by normalized name

        // Collect stats per player (only from matches they won, as that's when stats are recorded)
        filteredData.value.forEach(row => {
            const key = row.playerNormalized
            if (!key) return

            if (!playerStats[key]) {
                playerStats[key] = {
                    displayName: row.player,
                    firstServePct: [],
                    aces: [],
                    doubleFaults: [],
                    fastestServe: [],
                    avgFirstServeSpeed: [],
                    avgSecondServeSpeed: [],
                    winners: [],
                    forcedErrors: [],
                    unforcedErrors: [],
                    totalPointsWon: [],
                    netPointsWonPct: [],
                    returnPointsWonPct: [],
                    returnWinners: [],
                    breakPointsWonPct: [],
                    breaksPerGamePct: [],
                    setPointsSaved: [],
                    matchPointsSaved: [],
                    shortRalliesWonPct: [],
                    mediumRalliesWonPct: [],
                    longRalliesWonPct: [],
                    avgRallyLength: [],
                    firstServeWonPct: [],
                    secondServeWonPct: [],
                    matches: 0,
                }
            }

            const ps = playerStats[key]
            ps.matches++

            // Push valid values to arrays
            if (row.firstServePct !== null) ps.firstServePct.push(row.firstServePct)
            if (row.aces !== null) ps.aces.push(row.aces)
            if (row.doubleFaults !== null) ps.doubleFaults.push(row.doubleFaults)
            if (row.fastestServe !== null) ps.fastestServe.push(row.fastestServe)
            if (row.avgFirstServeSpeed !== null) ps.avgFirstServeSpeed.push(row.avgFirstServeSpeed)
            if (row.avgSecondServeSpeed !== null) ps.avgSecondServeSpeed.push(row.avgSecondServeSpeed)
            if (row.winners !== null) ps.winners.push(row.winners)
            if (row.forcedErrors !== null) ps.forcedErrors.push(row.forcedErrors)
            if (row.unforcedErrors !== null) ps.unforcedErrors.push(row.unforcedErrors)
            if (row.totalPointsWon !== null) ps.totalPointsWon.push(row.totalPointsWon)
            if (row.netPointsWonPct !== null) ps.netPointsWonPct.push(row.netPointsWonPct)
            if (row.returnPointsWonPct !== null) ps.returnPointsWonPct.push(row.returnPointsWonPct)
            if (row.returnWinners !== null) ps.returnWinners.push(row.returnWinners)
            if (row.breakPointsWonPct !== null) ps.breakPointsWonPct.push(row.breakPointsWonPct)
            if (row.breaksPerGamePct !== null) ps.breaksPerGamePct.push(row.breaksPerGamePct)
            if (row.setPointsSaved !== null) ps.setPointsSaved.push(row.setPointsSaved)
            if (row.matchPointsSaved !== null) ps.matchPointsSaved.push(row.matchPointsSaved)
            if (row.shortRalliesWonPct !== null) ps.shortRalliesWonPct.push(row.shortRalliesWonPct)
            if (row.mediumRalliesWonPct !== null) ps.mediumRalliesWonPct.push(row.mediumRalliesWonPct)
            if (row.longRalliesWonPct !== null) ps.longRalliesWonPct.push(row.longRalliesWonPct)
            if (row.avgRallyLength !== null) ps.avgRallyLength.push(row.avgRallyLength)
            if (row.firstServeWonPct !== null) ps.firstServeWonPct.push(row.firstServeWonPct)
            if (row.secondServeWonPct !== null) ps.secondServeWonPct.push(row.secondServeWonPct)

            // Also collect opponent stats (loser's stats from opp* fields)
            const oppKey = row.opponentNormalized
            if (oppKey) {
                if (!playerStats[oppKey]) {
                    playerStats[oppKey] = {
                        displayName: row.opponent,
                        firstServePct: [],
                        aces: [],
                        doubleFaults: [],
                        fastestServe: [],
                        avgFirstServeSpeed: [],
                        avgSecondServeSpeed: [],
                        winners: [],
                        forcedErrors: [],
                        unforcedErrors: [],
                        totalPointsWon: [],
                        netPointsWonPct: [],
                        returnPointsWonPct: [],
                        returnWinners: [],
                        breakPointsWonPct: [],
                        breaksPerGamePct: [],
                        setPointsSaved: [],
                        matchPointsSaved: [],
                        shortRalliesWonPct: [],
                        mediumRalliesWonPct: [],
                        longRalliesWonPct: [],
                        avgRallyLength: [],
                        firstServeWonPct: [],
                        secondServeWonPct: [],
                        matches: 0,
                    }
                }

                const ops = playerStats[oppKey]
                ops.matches++

                // Push opponent stats from opp* fields
                if (row.oppFirstServePct !== null && row.oppFirstServePct !== undefined) ops.firstServePct.push(row.oppFirstServePct)
                if (row.oppAces !== null && row.oppAces !== undefined) ops.aces.push(row.oppAces)
                if (row.oppDoubleFaults !== null && row.oppDoubleFaults !== undefined) ops.doubleFaults.push(row.oppDoubleFaults)
                if (row.oppFastestServe !== null && row.oppFastestServe !== undefined) ops.fastestServe.push(row.oppFastestServe)
                if (row.oppAvgFirstServeSpeed !== null && row.oppAvgFirstServeSpeed !== undefined) ops.avgFirstServeSpeed.push(row.oppAvgFirstServeSpeed)
                if (row.oppAvgSecondServeSpeed !== null && row.oppAvgSecondServeSpeed !== undefined) ops.avgSecondServeSpeed.push(row.oppAvgSecondServeSpeed)
                if (row.oppWinners !== null && row.oppWinners !== undefined) ops.winners.push(row.oppWinners)
                if (row.oppForcedErrors !== null && row.oppForcedErrors !== undefined) ops.forcedErrors.push(row.oppForcedErrors)
                if (row.oppUnforcedErrors !== null && row.oppUnforcedErrors !== undefined) ops.unforcedErrors.push(row.oppUnforcedErrors)
                if (row.oppTotalPointsWon !== null && row.oppTotalPointsWon !== undefined) ops.totalPointsWon.push(row.oppTotalPointsWon)
                if (row.oppNetPointsWonPct !== null && row.oppNetPointsWonPct !== undefined) ops.netPointsWonPct.push(row.oppNetPointsWonPct)
                if (row.oppReturnPointsWonPct !== null && row.oppReturnPointsWonPct !== undefined) ops.returnPointsWonPct.push(row.oppReturnPointsWonPct)
                if (row.oppReturnWinners !== null && row.oppReturnWinners !== undefined) ops.returnWinners.push(row.oppReturnWinners)
                if (row.oppBreakPointsWonPct !== null && row.oppBreakPointsWonPct !== undefined) ops.breakPointsWonPct.push(row.oppBreakPointsWonPct)
                if (row.oppBreaksPerGamePct !== null && row.oppBreaksPerGamePct !== undefined) ops.breaksPerGamePct.push(row.oppBreaksPerGamePct)
                if (row.oppFirstServeWonPct !== null && row.oppFirstServeWonPct !== undefined) ops.firstServeWonPct.push(row.oppFirstServeWonPct)
                if (row.oppSecondServeWonPct !== null && row.oppSecondServeWonPct !== undefined) ops.secondServeWonPct.push(row.oppSecondServeWonPct)
            }
        })

        // Calculate average stats per player
        const result = []
        for (const [key, stats] of Object.entries(playerStats)) {
            result.push({
                name: stats.displayName,
                matches: stats.matches,
                firstServePct: average(stats.firstServePct),
                aces: average(stats.aces),
                doubleFaults: average(stats.doubleFaults),
                fastestServe: average(stats.fastestServe),
                avgFirstServeSpeed: average(stats.avgFirstServeSpeed),
                avgSecondServeSpeed: average(stats.avgSecondServeSpeed),
                winners: average(stats.winners),
                forcedErrors: average(stats.forcedErrors),
                unforcedErrors: average(stats.unforcedErrors),
                totalPointsWon: average(stats.totalPointsWon),
                netPointsWonPct: average(stats.netPointsWonPct),
                returnPointsWonPct: average(stats.returnPointsWonPct),
                returnWinners: average(stats.returnWinners),
                breakPointsWonPct: average(stats.breakPointsWonPct),
                breaksPerGamePct: average(stats.breaksPerGamePct),
                setPointsSaved: average(stats.setPointsSaved),
                matchPointsSaved: average(stats.matchPointsSaved),
                shortRalliesWonPct: average(stats.shortRalliesWonPct),
                mediumRalliesWonPct: average(stats.mediumRalliesWonPct),
                longRalliesWonPct: average(stats.longRalliesWonPct),
                avgRallyLength: average(stats.avgRallyLength),
                firstServeWonPct: average(stats.firstServeWonPct),
                secondServeWonPct: average(stats.secondServeWonPct),
            })
        }

        // If player filter is active, only show that player's stats
        const playerFilter = filters.value.player?.toLowerCase()
        let filteredResult = playerFilter
            ? result.filter(p => p.name.toLowerCase().includes(playerFilter))
            : result

        // Require at least 5 matches (unless searching for a specific player)
        if (!playerFilter) {
            filteredResult = filteredResult.filter(p => p.matches >= 5)
        }

        return filteredResult.sort((a, b) => b.matches - a.matches)
    })

    // Set player filter from suggestion
    function selectPlayer(playerName) {
        filters.value.player = playerName
    }

    // Set player filter (for debounced input)
    function setPlayerFilter(value) {
        filters.value.player = value
    }

    // Reset filters
    function resetFilters() {
        filters.value = {
            player: '',
            tournament: '',
            dateStart: '',
            dateEnd: '',
        }
    }

    return {
        // State
        data,
        isLoading,
        error,
        filters,
        activeTab,
        // Getters
        uniquePlayers,
        uniqueTournaments,
        playerSuggestions,
        filteredData,
        playerRankings,
        statsLeaders,
        // Actions
        fetchData,
        selectPlayer,
        setPlayerFilter,
        resetFilters,
    }
})
