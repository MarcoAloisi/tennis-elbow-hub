// frontend/src/stores/predictions.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiUrl } from '@/config/api'
import { useAuthStore } from '@/stores/auth'

export interface PlayerInfo {
    name: string
    seed: number | null
    player_id: string | null
}

export interface DrawMatch {
    id: string
    section: 'main' | 'qualifying'
    round: string
    player1: PlayerInfo
    player2: PlayerInfo
    winner: string | null
    score: string | null
}

export interface DrawData {
    name: string
    surface: string
    category: string
    draw_size: number
    week: string
    year: string
    matches: DrawMatch[]
}

export interface Tournament {
    id: number
    name: string
    slug: string
    managames_url?: string
    trn_id?: number
    draw_data?: DrawData
    status: 'open' | 'closed' | 'finished'
    predictions_close_at: string
    created_at: string
    updated_at?: string
    entry_count: number
}

export interface PredictionEntry {
    id: number
    tournament_id: number
    nickname: string
    picks: Record<string, { winner: string; score?: string }>
    total_score: number
    submitted_at: string
}

export interface PickData {
    winner: string
    score?: string
}

const STORAGE_KEY_PREFIX = 'prediction_submitted_'
const STORAGE_NICK_KEY = 'prediction_nickname'

export const usePredictionsStore = defineStore('predictions', () => {
    const tournaments = ref<Tournament[]>([])
    const activeTournament = ref<Tournament | null>(null)
    const entries = ref<PredictionEntry[]>([])
    const myPicks = ref<Record<string, PickData>>({})
    const myNickname = ref<string>(localStorage.getItem(STORAGE_NICK_KEY) || '')
    const loading = ref(false)
    const error = ref<string | null>(null)

    // IDs of tournaments the user has submitted to (from localStorage)
    const submittedIds = computed<Set<number>>(() => {
        const ids = new Set<number>()
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i)
            if (key?.startsWith(STORAGE_KEY_PREFIX)) {
                const id = parseInt(key.replace(STORAGE_KEY_PREFIX, ''), 10)
                if (!isNaN(id)) ids.add(id)
            }
        }
        return ids
    })

    function hasSubmitted(tournamentId: number): boolean {
        return localStorage.getItem(`${STORAGE_KEY_PREFIX}${tournamentId}`) === '1'
    }

    function markSubmitted(tournamentId: number, nickname: string): void {
        localStorage.setItem(`${STORAGE_KEY_PREFIX}${tournamentId}`, '1')
        localStorage.setItem(STORAGE_NICK_KEY, nickname)
        myNickname.value = nickname
    }

    async function fetchTournaments(): Promise<void> {
        loading.value = true
        error.value = null
        try {
            const res = await fetch(apiUrl('/api/predictions/tournaments'))
            if (!res.ok) throw new Error(`Failed to load tournaments: ${res.statusText}`)
            tournaments.value = await res.json()
        } catch (err: any) {
            error.value = err.message
        } finally {
            loading.value = false
        }
    }

    async function fetchTournament(slug: string): Promise<void> {
        loading.value = true
        error.value = null
        try {
            const res = await fetch(apiUrl(`/api/predictions/tournaments/${slug}`))
            if (!res.ok) throw new Error(`Failed to load tournament: ${res.statusText}`)
            activeTournament.value = await res.json()
        } catch (err: any) {
            error.value = err.message
        } finally {
            loading.value = false
        }
    }

    async function fetchEntries(tournamentId: number): Promise<void> {
        try {
            const res = await fetch(apiUrl(`/api/predictions/tournaments/${tournamentId}/entries`))
            if (!res.ok) throw new Error(`Failed to load entries: ${res.statusText}`)
            entries.value = await res.json()
        } catch (err: any) {
            error.value = err.message
        }
    }

    async function submitPrediction(tournamentId: number, nickname: string): Promise<void> {
        loading.value = true
        error.value = null
        try {
            const res = await fetch(apiUrl(`/api/predictions/tournaments/${tournamentId}/entries`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nickname: nickname.trim(), picks: myPicks.value }),
            })
            if (!res.ok) {
                const data = await res.json()
                throw new Error(data.detail || `Submission failed: ${res.statusText}`)
            }
            markSubmitted(tournamentId, nickname)
            await fetchEntries(tournamentId)
        } catch (err: any) {
            error.value = err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    function setPick(matchId: string, winner: string, score?: string): void {
        myPicks.value[matchId] = { winner, score: score || undefined }
    }

    function clearPicks(): void {
        myPicks.value = {}
    }

    // ─── Admin actions ──────────────────────────────────────────────────

    async function _adminPost(path: string, body?: object): Promise<any> {
        const authStore = useAuthStore()
        const token = authStore.session?.access_token
        if (!token) throw new Error('Not authenticated')
        const res = await fetch(apiUrl(path), {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: body ? JSON.stringify(body) : undefined,
        })
        if (!res.ok) {
            const data = await res.json().catch(() => ({}))
            throw new Error(data.detail || `Request failed: ${res.statusText}`)
        }
        return res.json().catch(() => null)
    }

    async function createTournament(managamesUrl: string, closeAt: string): Promise<Tournament> {
        const t = await _adminPost('/api/predictions/tournaments', {
            managames_url: managamesUrl,
            predictions_close_at: closeAt,
        })
        await fetchTournaments()
        return t
    }

    async function refreshResults(tournamentId: number): Promise<void> {
        await _adminPost(`/api/predictions/tournaments/${tournamentId}/refresh`)
        if (activeTournament.value?.id === tournamentId) {
            await fetchTournament(activeTournament.value.slug)
        }
        await fetchEntries(tournamentId)
    }

    async function closePredictions(tournamentId: number): Promise<void> {
        await _adminPost(`/api/predictions/tournaments/${tournamentId}/close`)
        await fetchTournaments()
        if (activeTournament.value?.id === tournamentId) {
            activeTournament.value.status = 'closed'
        }
    }

    async function markFinished(tournamentId: number): Promise<void> {
        await _adminPost(`/api/predictions/tournaments/${tournamentId}/finish`)
        await fetchTournaments()
        if (activeTournament.value?.id === tournamentId) {
            activeTournament.value.status = 'finished'
        }
    }

    async function deleteEntry(entryId: number): Promise<void> {
        const authStore = useAuthStore()
        const token = authStore.session?.access_token
        if (!token) throw new Error('Not authenticated')
        const res = await fetch(apiUrl(`/api/predictions/entries/${entryId}`), {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
        })
        if (!res.ok) throw new Error(`Failed to delete entry: ${res.statusText}`)
        entries.value = entries.value.filter(e => e.id !== entryId)
    }

    async function deleteTournament(tournamentId: number): Promise<void> {
        const authStore = useAuthStore()
        const token = authStore.session?.access_token
        if (!token) throw new Error('Not authenticated')
        const res = await fetch(apiUrl(`/api/predictions/tournaments/${tournamentId}`), {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
        })
        if (!res.ok) throw new Error(`Failed to delete tournament: ${res.statusText}`)
        await fetchTournaments()
    }

    return {
        tournaments, activeTournament, entries, myPicks, myNickname,
        loading, error, submittedIds,
        hasSubmitted, markSubmitted,
        fetchTournaments, fetchTournament, fetchEntries, submitPrediction,
        setPick, clearPicks,
        createTournament, refreshResults, closePredictions, markFinished,
        deleteEntry, deleteTournament,
    }
})
