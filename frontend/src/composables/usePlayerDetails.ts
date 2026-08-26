/**
 * Composable for fetching individual player details (match history, W/L, activity).
 */
import { ref } from 'vue'
import { apiUrl } from '@/config/api'
import { supabase } from '@/config/supabase'

interface MatchEntry {
  opponent: string
  score: string | null
  date: string | null
  player_elo: number | null
  opponent_elo: number | null
  result: 'W' | 'L' | '?'
}

interface PlayerDetails {
  name: string
  total_matches: number
  wins: number
  losses: number
  win_rate: number
  matches_last_7_days: number
  matches_last_30_days: number
  best_win: MatchEntry | null
  worst_loss: MatchEntry | null
  recent_matches: MatchEntry[]
  error?: string
}

export function usePlayerDetails() {
  const details = ref<PlayerDetails | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function getAuthHeaders(): Promise<Record<string, string>> {
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token
    if (!token) {
      throw new Error('Not authenticated')
    }
    return { Authorization: `Bearer ${token}` }
  }

  let requestId = 0

  async function fetchPlayerDetails(playerName: string, elo: number): Promise<void> {
    const thisRequest = ++requestId
    isLoading.value = true
    error.value = null
    details.value = null

    try {
      const headers = await getAuthHeaders()
      const response = await fetch(
        apiUrl(`/api/players/${encodeURIComponent(playerName)}?elo=${elo}`),
        { headers }
      )

      if (thisRequest !== requestId) return

      if (response.status === 401) {
        throw new Error('Session expired — log in again.')
      }
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`)
      }

      details.value = await response.json()
    } catch (e: any) {
      if (thisRequest !== requestId) return
      error.value = e.message
      console.error('Failed to fetch player details:', e)
    } finally {
      if (thisRequest === requestId) {
        isLoading.value = false
      }
    }
  }

  function clearDetails(): void {
    requestId++
    details.value = null
    error.value = null
    isLoading.value = false
  }

  return {
    details,
    isLoading,
    error,
    fetchPlayerDetails,
    clearDetails,
  }
}
