/**
 * Composable for managing player nickname/alias mappings.
 * Handles CRUD operations against the admin aliases API.
 */
import { ref, computed, onMounted } from 'vue'
import { apiUrl } from '@/config/api'
import { supabase } from '@/config/supabase'

interface AliasRecord {
  id: number
  alias: string
  canonical_name: string
}

interface GroupedAlias {
  canonical_name: string
  aliases: string[]
}

export function useNicknameMapping() {
  const aliases = ref<AliasRecord[]>([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const successMessage = ref<string | null>(null)

  async function getAuthHeaders(): Promise<Record<string, string>> {
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token
    if (!token) throw new Error('Not authenticated')
    return { Authorization: `Bearer ${token}` }
  }

  async function fetchAliases() {
    isLoading.value = true
    error.value = null
    try {
      const headers = await getAuthHeaders()
      const response = await fetch(apiUrl('/api/admin/aliases'), { headers })
      if (!response.ok) throw new Error(`HTTP error ${response.status}`)
      aliases.value = await response.json()
    } catch (e: any) {
      error.value = e.message
    } finally {
      isLoading.value = false
    }
  }

  async function saveAliases(canonicalName: string, newAliases: string[]) {
    isSaving.value = true
    error.value = null
    successMessage.value = null
    try {
      const headers = await getAuthHeaders()
      const response = await fetch(apiUrl('/api/admin/aliases'), {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          canonical_name: canonicalName,
          aliases: newAliases,
        }),
      })
      if (!response.ok) throw new Error(`HTTP error ${response.status}`)
      const result = await response.json()
      const createdCount = result.created?.length ?? 0
      const skippedCount = result.skipped?.length ?? 0
      successMessage.value = `${createdCount} alias(es) created${skippedCount ? `, ${skippedCount} skipped (already exist)` : ''}`
      await fetchAliases()
    } catch (e: any) {
      error.value = e.message
    } finally {
      isSaving.value = false
    }
  }

  async function deleteAlias(alias: string) {
    error.value = null
    try {
      const headers = await getAuthHeaders()
      const response = await fetch(apiUrl(`/api/admin/aliases/${encodeURIComponent(alias)}`), {
        method: 'DELETE',
        headers,
      })
      if (!response.ok) throw new Error(`HTTP error ${response.status}`)
      await fetchAliases()
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function renameCanonical(oldName: string, newName: string) {
    isSaving.value = true
    error.value = null
    successMessage.value = null
    try {
      const headers = await getAuthHeaders()
      const response = await fetch(apiUrl('/api/admin/aliases/rename'), {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_name: oldName, new_name: newName }),
      })
      if (!response.ok) throw new Error(`HTTP error ${response.status}`)
      successMessage.value = `Renamed "${oldName}" → "${newName}"`
      await fetchAliases()
    } catch (e: any) {
      error.value = e.message
    } finally {
      isSaving.value = false
    }
  }

  /**
   * Group flat alias list by canonical_name for display.
   */
  const groupedAliases = computed<GroupedAlias[]>(() => {
    const map = new Map<string, string[]>()
    for (const a of aliases.value) {
      if (!map.has(a.canonical_name)) {
        map.set(a.canonical_name, [])
      }
      map.get(a.canonical_name)!.push(a.alias)
    }
    return Array.from(map.entries())
      .map(([canonical_name, aliasList]) => ({ canonical_name, aliases: aliasList }))
      .sort((a, b) => a.canonical_name.localeCompare(b.canonical_name))
  })

  function clearError() {
    error.value = null
  }

  function clearSuccess() {
    successMessage.value = null
  }

  onMounted(() => {
    fetchAliases()
  })

  return {
    aliases,
    groupedAliases,
    isLoading,
    isSaving,
    error,
    successMessage,
    fetchAliases,
    saveAliases,
    deleteAlias,
    renameCanonical,
    clearError,
    clearSuccess,
  }
}
