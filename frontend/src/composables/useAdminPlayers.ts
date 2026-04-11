/**
 * Composable for admin players database functionality.
 * Handles fetching, searching, sorting, auto-refresh, and export.
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { apiUrl } from '@/config/api'
import { supabase } from '@/config/supabase'

export interface PlayerRecord {
  name: string
  latest_elo: number | null
  total_matches: number
  last_match_date: string | null
}

export type SortField = 'name' | 'latest_elo' | 'total_matches' | 'last_match_date'
export type SortDirection = 'asc' | 'desc'

export function useAdminPlayers() {
  const players = ref<PlayerRecord[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const lastRefreshed = ref<string | null>(null)
  const searchQuery = ref('')
  const sortField = ref<SortField>('total_matches')
  const sortDirection = ref<SortDirection>('desc')

  // Range filters
  const eloMin = ref<number | null>(null)
  const eloMax = ref<number | null>(null)
  const matchesMin = ref<number | null>(null)
  const matchesMax = ref<number | null>(null)

  let autoRefreshTimer: ReturnType<typeof setInterval> | null = null

  // 24 hours in ms
  const AUTO_REFRESH_INTERVAL = 24 * 60 * 60 * 1000

  async function getAuthHeaders(): Promise<Record<string, string>> {
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token
    if (!token) {
      throw new Error('Not authenticated')
    }
    return { Authorization: `Bearer ${token}` }
  }

  async function fetchPlayers() {
    isLoading.value = true
    error.value = null

    try {
      const headers = await getAuthHeaders()
      const response = await fetch(apiUrl('/api/admin/players'), { headers })

      if (response.status === 401 || response.status === 403) {
        throw new Error('Unauthorized — admin access required')
      }
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`)
      }

      players.value = await response.json()
      lastRefreshed.value = new Date().toISOString()
    } catch (e: any) {
      error.value = e.message
      console.error('Failed to fetch players:', e)
    } finally {
      isLoading.value = false
    }
  }

  async function downloadCsv() {
    try {
      const headers = await getAuthHeaders()
      const response = await fetch(apiUrl('/api/admin/players/csv'), { headers })

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`)
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `players_database_${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (e: any) {
      error.value = `Download failed: ${e.message}`
    }
  }

  function openInGoogleSheets() {
    // Google Sheets can import from a public URL, but since our endpoint
    // requires auth, we generate the CSV client-side and open it in Sheets
    const csvRows = [
      ['Player Name', 'Latest ELO', 'Total Matches', 'Last Match Date'],
      ...filteredAndSortedPlayers.value.map(p => [
        p.name,
        p.latest_elo ?? '',
        p.total_matches,
        p.last_match_date ?? ''
      ])
    ]
    const csvContent = csvRows.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)

    // Use Google Sheets' paste from clipboard approach - open a new sheet
    // Since we can't directly import a blob, we'll download and let user import
    // Actually, let's use the data URI approach with encodeURIComponent
    const encodedCsv = encodeURIComponent(csvContent)
    const googleSheetsUrl = `https://docs.google.com/spreadsheets/d/e/create?usp=sharing`
    
    // Best approach: download CSV then user imports to Google Sheets
    // Alternative: create a Google Sheet from CSV data URI
    // For simplicity, we open Google Sheets new and provide CSV download
    window.open('https://sheets.new', '_blank')
    
    // Also trigger download so user can import it
    const a = document.createElement('a')
    a.href = url
    a.download = `players_database_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  }

  function setSort(field: SortField) {
    if (sortField.value === field) {
      sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortField.value = field
      sortDirection.value = field === 'name' ? 'asc' : 'desc'
    }
  }

  /** Players list after excluding doubles/pair entries (names with '&'). */
  const cleanPlayers = computed(() =>
    players.value.filter(p => !p.name.includes('&'))
  )

  const filteredAndSortedPlayers = computed(() => {
    let result = [...cleanPlayers.value]

    // Filter by search query
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(p => p.name.toLowerCase().includes(query))
    }

    // Filter by ELO range
    if (eloMin.value !== null) {
      result = result.filter(p => (p.latest_elo ?? 0) >= eloMin.value!)
    }
    if (eloMax.value !== null) {
      result = result.filter(p => (p.latest_elo ?? 0) <= eloMax.value!)
    }

    // Filter by matches range
    if (matchesMin.value !== null) {
      result = result.filter(p => p.total_matches >= matchesMin.value!)
    }
    if (matchesMax.value !== null) {
      result = result.filter(p => p.total_matches <= matchesMax.value!)
    }

    // Sort
    result.sort((a, b) => {
      const dir = sortDirection.value === 'asc' ? 1 : -1

      if (sortField.value === 'name') {
        return dir * a.name.localeCompare(b.name)
      }
      if (sortField.value === 'latest_elo') {
        const aElo = a.latest_elo ?? 0
        const bElo = b.latest_elo ?? 0
        return dir * (aElo - bElo)
      }
      if (sortField.value === 'total_matches') {
        return dir * (a.total_matches - b.total_matches)
      }
      if (sortField.value === 'last_match_date') {
        const aDate = a.last_match_date ?? ''
        const bDate = b.last_match_date ?? ''
        return dir * aDate.localeCompare(bDate)
      }
      return 0
    })

    return result
  })

  /* ─── KPI Computed Properties ─── */
  const highestEloEntry = computed(() => {
    const withElo = cleanPlayers.value.filter(p => p.latest_elo !== null)
    if (!withElo.length) return null
    return withElo.reduce((best, p) => (p.latest_elo! > best.latest_elo!) ? p : best)
  })

  const highestElo = computed(() => highestEloEntry.value?.latest_elo ?? null)
  const highestEloPlayer = computed(() => highestEloEntry.value?.name ?? null)

  const lowestEloEntry = computed(() => {
    const withElo = cleanPlayers.value.filter(p => p.latest_elo !== null)
    if (!withElo.length) return null
    return withElo.reduce((best, p) => (p.latest_elo! < best.latest_elo!) ? p : best)
  })

  const lowestElo = computed(() => lowestEloEntry.value?.latest_elo ?? null)
  const lowestEloPlayer = computed(() => lowestEloEntry.value?.name ?? null)

  const avgElo = computed(() => {
    const elos = cleanPlayers.value.map(p => p.latest_elo).filter((e): e is number => e !== null)
    if (!elos.length) return null
    return Math.round(elos.reduce((sum, e) => sum + e, 0) / elos.length)
  })

  const avgMatchesPlayed = computed(() => {
    if (!cleanPlayers.value.length) return null
    const total = cleanPlayers.value.reduce((sum, p) => sum + p.total_matches, 0)
    return Math.round((total / cleanPlayers.value.length) * 10) / 10
  })

  function startAutoRefresh() {
    autoRefreshTimer = setInterval(fetchPlayers, AUTO_REFRESH_INTERVAL)
  }

  function stopAutoRefresh() {
    if (autoRefreshTimer) {
      clearInterval(autoRefreshTimer)
      autoRefreshTimer = null
    }
  }

  function clearError() {
    error.value = null
  }

  onMounted(() => {
    fetchPlayers()
    startAutoRefresh()
  })

  onUnmounted(() => {
    stopAutoRefresh()
  })

  function clearFilters() {
    eloMin.value = null
    eloMax.value = null
    matchesMin.value = null
    matchesMax.value = null
  }

  return {
    players: filteredAndSortedPlayers,
    allPlayers: cleanPlayers,
    isLoading,
    error,
    lastRefreshed,
    searchQuery,
    sortField,
    sortDirection,
    eloMin,
    eloMax,
    matchesMin,
    matchesMax,
    highestElo,
    highestEloPlayer,
    lowestElo,
    lowestEloPlayer,
    avgElo,
    avgMatchesPlayed,
    fetchPlayers,
    downloadCsv,
    openInGoogleSheets,
    setSort,
    clearError,
    clearFilters,
  }
}
