import { ref, onMounted, onUnmounted } from 'vue'
import { apiUrl } from '@/config/api'

export interface RealTennisScore {
  sets: [number, number][]
  current_game: string | null
}

export interface RealTennisTournament {
  id: number
  name: string
  category: string
  round: string
  match_count: number
}

export interface RealTennisMatch {
  id: number
  player1: string
  player2: string
  score: RealTennisScore
  status: 'live' | 'upcoming' | 'completed'
  start_timestamp: number | null
  tournament: RealTennisTournament
}

interface RealTennisResponse {
  live: RealTennisMatch[]
  upcoming: RealTennisMatch[]
  completed: RealTennisMatch[]
  tournaments: RealTennisTournament[]
  cached_at: string | null
  stale: boolean
}

const POLL_INTERVAL_MS = 30_000

export function useRealTennis() {
  const live = ref<RealTennisMatch[]>([])
  const upcoming = ref<RealTennisMatch[]>([])
  const completed = ref<RealTennisMatch[]>([])
  const tournaments = ref<RealTennisTournament[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const stale = ref(false)

  let pollInterval: ReturnType<typeof setInterval> | null = null

  async function fetchScores() {
    try {
      const res = await fetch(apiUrl('/api/real-tennis/scores'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: RealTennisResponse = await res.json()
      live.value = data.live
      upcoming.value = data.upcoming
      completed.value = data.completed
      tournaments.value = data.tournaments
      stale.value = data.stale
      error.value = null
    } catch {
      error.value = 'Failed to load tennis scores'
    } finally {
      isLoading.value = false
    }
  }

  onMounted(() => {
    isLoading.value = true
    fetchScores()
    pollInterval = setInterval(fetchScores, POLL_INTERVAL_MS)
  })

  onUnmounted(() => {
    if (pollInterval !== null) clearInterval(pollInterval)
  })

  return { live, upcoming, completed, tournaments, isLoading, error, stale, fetchScores }
}
