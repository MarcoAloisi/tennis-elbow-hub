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
    const activeTab = ref('data') // 'data', 'leaders' (rankings removed)

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

    // Data - now we just process the raw data slightly, no more winner filtering
    const data = computed(() => {
        return rawData.value.map(row => ({
            ...row,
            // Normalize for easy filtering
            playerNormalized: normalizePlayerKey(row.player),
            opponentNormalized: normalizePlayerKey(row.opponent),
            tournamentNormalized: normalizeTournament(row.tournament)
        }))
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
        // Handle various date formats if needed, but assuming DD/MM/YYYY given clean_date
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

    // Stats leaders - average stats per player
    // Aggregates data from ALL rows where the player appears in the 'player' column
    const statsLeaders = computed(() => {
        const playerStats = {} // keyed by normalized name

        // Use filteredData so we can see leaders for specific tournaments/dates if desired
        // Or should we use global data? Usually leaders are global, but filtering is nice.
        // Let's use filteredData to allow "Leaders in 2024" etc.
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
        })

        // Calculate average stats per player
        // Note: We do NOT include opponent stats here because in the new data format,
        // each row represents ONE player's stats (the 'Player' column).
        // The opponent's stats are in a separate row where THEY are the 'Player'.

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
        let finalResult = playerFilter
            ? result.filter(p => p.name.toLowerCase().includes(playerFilter))
            : result

        // Require at least 5 matches (unless searching for a specific player)
        if (!playerFilter) {
            finalResult = finalResult.filter(p => p.matches >= 5)
        }

        return finalResult.sort((a, b) => b.matches - a.matches)
    })

    // Tour-wide average stats (aggregate all players)
    const tourAverage = computed(() => {
        const allStats = statsLeaders.value
        if (!allStats.length) return null

        const avg = (arr, key) => {
            const vals = arr.map(p => p[key]).filter(v => v !== null && v !== undefined)
            return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null
        }

        const totalMatches = allStats.reduce((sum, p) => sum + p.matches, 0)

        return {
            name: 'Tour Average',
            playerCount: allStats.length,
            matches: totalMatches,
            firstServePct: avg(allStats, 'firstServePct'),
            aces: avg(allStats, 'aces'),
            doubleFaults: avg(allStats, 'doubleFaults'),
            fastestServe: avg(allStats, 'fastestServe'),
            avgFirstServeSpeed: avg(allStats, 'avgFirstServeSpeed'),
            avgSecondServeSpeed: avg(allStats, 'avgSecondServeSpeed'),
            winners: avg(allStats, 'winners'),
            forcedErrors: avg(allStats, 'forcedErrors'),
            unforcedErrors: avg(allStats, 'unforcedErrors'),
            totalPointsWon: avg(allStats, 'totalPointsWon'),
            netPointsWonPct: avg(allStats, 'netPointsWonPct'),
            returnPointsWonPct: avg(allStats, 'returnPointsWonPct'),
            returnWinners: avg(allStats, 'returnWinners'),
            breakPointsWonPct: avg(allStats, 'breakPointsWonPct'),
            breaksPerGamePct: avg(allStats, 'breaksPerGamePct'),
            setPointsSaved: avg(allStats, 'setPointsSaved'),
            matchPointsSaved: avg(allStats, 'matchPointsSaved'),
            shortRalliesWonPct: avg(allStats, 'shortRalliesWonPct'),
            mediumRalliesWonPct: avg(allStats, 'mediumRalliesWonPct'),
            longRalliesWonPct: avg(allStats, 'longRalliesWonPct'),
            avgRallyLength: avg(allStats, 'avgRallyLength'),
            firstServeWonPct: avg(allStats, 'firstServeWonPct'),
            secondServeWonPct: avg(allStats, 'secondServeWonPct'),
        }
    })

    // Current stats to display: filtered player or tour average
    const currentPlayerStats = computed(() => {
        const playerFilter = filters.value.player?.toLowerCase()

        if (playerFilter) {
            // Find exact match first, then partial match
            const exactMatch = statsLeaders.value.find(
                p => p.name.toLowerCase() === playerFilter
            )
            if (exactMatch) return exactMatch

            // Partial match - return first player that matches
            const partialMatch = statsLeaders.value.find(
                p => p.name.toLowerCase().includes(playerFilter)
            )
            if (partialMatch) return partialMatch
        }

        // No filter or no match - return tour average
        return tourAverage.value
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

    // Get the latest match date from the data (for "last updated" display)
    const latestMatchDate = computed(() => {
        if (!data.value.length) return null

        let latestDate = null
        let latestDateStr = null

        data.value.forEach(row => {
            if (row.date) {
                const rowDate = parseDate(row.date)
                if (rowDate && (!latestDate || rowDate > latestDate)) {
                    latestDate = rowDate
                    latestDateStr = row.date
                }
            }
        })

        return latestDateStr
    })

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
        statsLeaders,
        tourAverage,
        currentPlayerStats,
        latestMatchDate,
        // Actions
        fetchData,
        selectPlayer,
        setPlayerFilter,
        resetFilters,
    }
})
