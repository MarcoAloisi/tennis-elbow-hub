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
        tour: 'all', // 'all', 'atp', 'wta', 'dubs'
    })

    // Active subtab
    const activeTab = ref('data') // 'data', 'leaders' (rankings removed)

    // Fetch data from API - one request for the whole (atp+wta+dubs) dataset,
    // since it's all aggregated client-side anyway (leaderboards, filters)
    async function fetchData() {
        isLoading.value = true
        error.value = null

        try {
            const response = await fetch(`${API_BASE}/api/tour-logs?page_size=10000`)
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
            // Tour filter
            if (filters.value.tour && filters.value.tour !== 'all' && row.tour !== filters.value.tour) {
                return false
            }

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

    const STAT_KEYS = [
        'firstServePct', 'aces', 'doubleFaults', 'fastestServe',
        'avgFirstServeSpeed', 'avgSecondServeSpeed', 'winners', 'forcedErrors',
        'unforcedErrors', 'totalPointsWon', 'netPointsWonPct', 'returnPointsWonPct',
        'returnWinners', 'breakPointsWonPct', 'breaksPerGamePct', 'setPointsSaved',
        'matchPointsSaved', 'shortRalliesWonPct', 'mediumRalliesWonPct',
        'longRalliesWonPct', 'avgRallyLength', 'firstServeWonPct', 'secondServeWonPct',
    ]

    // Stats leaders - average stats per player, one match = one uniqueId (sheet's
    // "Unique ID B" column), not one row. A match can span multiple rows (e.g.
    // misnumbered duplicate exports); those rows are collapsed into a single
    // match-level value per stat before averaging, so every match counts once
    // and each stat gets its own denominator (a match missing Aces just doesn't
    // count toward the Aces average, but still counts toward the rest).
    const statsLeaders = computed(() => {
        // Group rows by player -> uniqueId -> [rows for that match]
        const playerMatches: Record<string, { displayName: string; matches: Map<string, any[]> }> = {}

        filteredData.value.forEach(row => {
            const key = row.playerNormalized
            if (!key) return

            if (!playerMatches[key]) {
                playerMatches[key] = { displayName: row.player, matches: new Map() }
            }
            const matchKey = row.uniqueId || row.matchId
            if (!matchKey) return

            const bucket = playerMatches[key].matches
            if (!bucket.has(matchKey)) bucket.set(matchKey, [])
            bucket.get(matchKey).push(row)
        })

        const result = []
        for (const [, { displayName, matches }] of Object.entries(playerMatches)) {
            // Collapse each match's rows into one value per stat (average of
            // whatever non-null values exist across the duplicate rows)
            const collapsedMatches = Array.from(matches.values()).map(rows => {
                const collapsed: Record<string, number | null> = {}
                for (const statKey of STAT_KEYS) {
                    collapsed[statKey] = average(rows.map(r => r[statKey]))
                }
                return collapsed
            })

            const stats: any = { displayName, matches: collapsedMatches.length }
            for (const statKey of STAT_KEYS) {
                stats[statKey] = average(collapsedMatches.map(m => m[statKey]))
            }
            result.push(stats)
        }

        return finalizeStatsLeaders(result)
    })

    // Apply player filter / minimum match count and shape final leader rows
    function finalizeStatsLeaders(playerStatsList) {
        const out = playerStatsList.map(({ displayName, ...stats }) => ({ name: displayName, ...stats }))

        // If player filter is active, only show that player's stats
        const playerFilter = filters.value.player?.toLowerCase()
        let finalResult = playerFilter
            ? out.filter(p => p.name.toLowerCase().includes(playerFilter))
            : out

        // Require at least 5 matches (unless searching for a specific player)
        if (!playerFilter) {
            finalResult = finalResult.filter(p => p.matches >= 5)
        }

        return finalResult.sort((a, b) => b.matches - a.matches)
    }

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
            tour: 'all',
        }
    }

    function clearError() {
        error.value = null
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
        clearError,
    }
})
