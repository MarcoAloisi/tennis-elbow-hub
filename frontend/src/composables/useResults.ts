/**
 * Composable for fetching finished TE4 match results (day/mod/player filtered, paginated).
 */
import { ref } from 'vue'
import { apiUrl } from '@/config/api'

export interface ResultEntry {
  match_id: string
  match_name: string
  winner: string | null
  score: string | null
  surface: string | null
  mod: string | null
  p1_elo: number | null
  p2_elo: number | null
}

interface ResultsResponse {
  results: ResultEntry[]
  date: string
  total: number
  page: number
  page_size: number
  total_pages: number
}

export function useResults() {
  const results = ref<ResultEntry[]>([])
  const total = ref(0)
  const totalPages = ref(1)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  let requestId = 0

  async function fetchResults(params: {
    date: string
    mod?: string | null
    player?: string
    page?: number
  }): Promise<void> {
    const thisRequest = ++requestId
    isLoading.value = true
    error.value = null

    try {
      const qs = new URLSearchParams({ date: params.date })
      if (params.mod) qs.set('mod', params.mod)
      if (params.player) qs.set('player', params.player)
      if (params.page) qs.set('page', String(params.page))

      const response = await fetch(apiUrl(`/api/scores/results?${qs}`))

      if (thisRequest !== requestId) return

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`)
      }

      const data: ResultsResponse = await response.json()
      results.value = data.results
      total.value = data.total
      totalPages.value = data.total_pages
    } catch (e: any) {
      if (thisRequest !== requestId) return
      error.value = e.message
      console.error('Failed to fetch results:', e)
    } finally {
      if (thisRequest === requestId) {
        isLoading.value = false
      }
    }
  }

  return {
    results,
    total,
    totalPages,
    isLoading,
    error,
    fetchResults,
  }
}
