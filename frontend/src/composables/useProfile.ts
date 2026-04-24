import { ref } from 'vue'
import { apiUrl } from '@/config/api'
import { supabase } from '@/config/supabase'

export interface PlayerStats {
  total_matches: number
  wins: number
  losses: number
  latest_elo: number | null
  last_match_date: string | null
}

export interface Profile {
  id: string
  display_name: string
  avatar_url: string | null
  bio: string | null
  birthday: string | null
  tours: string[] | null
  in_game_name: string | null
  player_name: string | null
  player_verified: boolean
  favorite_tennis_player: string | null
  favorite_tournament: string | null
  approved: boolean
  created_at: string
  player_stats: PlayerStats | null
}

export interface ProfileUpdate {
  display_name?: string
  bio?: string
  birthday?: string | null
  tours?: string[]
  in_game_name?: string
  player_name?: string | null
  favorite_tennis_player?: string
  favorite_tournament?: string
}

async function authHeaders(): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession()
  return { Authorization: `Bearer ${data.session?.access_token}` }
}

export function useProfile() {
  const profile = ref<Profile | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchMyProfile(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const headers = await authHeaders()
      const res = await fetch(apiUrl('/api/profile/me'), { headers })
      if (!res.ok) throw new Error('Failed to load profile')
      profile.value = await res.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchPublicProfile(userId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const headers = await authHeaders()
      const res = await fetch(apiUrl(`/api/profile/${userId}`), { headers })
      if (!res.ok) throw new Error('Profile not found')
      profile.value = await res.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(updates: ProfileUpdate): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const headers = await authHeaders()
      const res = await fetch(apiUrl('/api/profile/me'), {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      if (!res.ok) throw new Error('Failed to update profile')
      profile.value = await res.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function uploadAvatar(file: File): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const headers = await authHeaders()
      const form = new FormData()
      form.append('image', file)
      const res = await fetch(apiUrl('/api/profile/me/avatar'), {
        method: 'POST',
        headers,
        body: form,
      })
      if (!res.ok) throw new Error('Failed to upload avatar')
      profile.value = await res.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchPlayers(): Promise<string[]> {
    try {
      const headers = await authHeaders()
      const res = await fetch(apiUrl('/api/admin/players'), { headers })
      if (!res.ok) return []
      const data: { name: string }[] = await res.json()
      return data.map((p) => p.name).sort()
    } catch {
      return []
    }
  }

  return { profile, loading, error, fetchMyProfile, fetchPublicProfile, updateProfile, uploadAvatar, fetchPlayers }
}
