<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { supabase } from '@/config/supabase'
import { apiUrl } from '@/config/api'
import { RefreshCw, User } from 'lucide-vue-next'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'

interface AdminUser {
  user_id: string
  email: string | null
  display_name: string | null
  in_game_name: string | null
  player_name: string | null
  approved: boolean
  is_admin: boolean
  created_at: string
  online: boolean
}

const users = ref<AdminUser[]>([])
const isLoading = ref(false)
const error = ref('')

async function getAuthHeaders() {
  const { data } = await supabase.auth.getSession()
  return { Authorization: `Bearer ${data.session?.access_token}` }
}

async function fetchUsers() {
  isLoading.value = true
  error.value = ''
  try {
    const headers = await getAuthHeaders()
    const res = await fetch(apiUrl('/api/admin/users'), { headers })
    if (!res.ok) throw new Error(`Failed to load users (${res.status})`)
    users.value = await res.json()
  } catch (e: any) {
    error.value = e.message || 'Failed to load users.'
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchUsers)
</script>

<template>
  <div class="admin-users">
    <div class="admin-users-header">
      <h1><User :size="24" /> Registered Users</h1>
      <button class="btn-refresh" @click="fetchUsers" :disabled="isLoading">
        <RefreshCw :size="16" :class="{ spinning: isLoading }" /> Refresh
      </button>
    </div>

    <ErrorAlert v-if="error" :message="error" />
    <LoadingSpinner v-if="isLoading && !users.length" />

    <table v-if="users.length" class="users-table">
      <thead>
        <tr>
          <th>Status</th>
          <th>Display Name</th>
          <th>Email</th>
          <th>In-Game Name</th>
          <th>Role</th>
          <th>Approved</th>
          <th>Joined</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.user_id">
          <td>
            <span
              class="status-dot"
              :class="u.online ? 'online' : 'offline'"
              :title="u.online ? 'Online' : 'Offline'"
            ></span>
          </td>
          <td>{{ u.display_name || '—' }}</td>
          <td>{{ u.email || '—' }}</td>
          <td>{{ u.in_game_name || '—' }}</td>
          <td>{{ u.is_admin ? 'Admin' : 'User' }}</td>
          <td>{{ u.approved ? 'Yes' : 'No' }}</td>
          <td>{{ new Date(u.created_at).toLocaleDateString() }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!isLoading">No registered users yet.</p>
  </div>
</template>

<style scoped>
.admin-users {
  max-width: 900px;
  margin: 0 auto;
  padding: var(--space-6);
}

.admin-users-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.admin-users-header h1 {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-xl);
}

.btn-refresh {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.users-table {
  width: 100%;
  border-collapse: collapse;
}

.users-table th,
.users-table td {
  padding: var(--space-2) var(--space-3);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.status-dot.online {
  background: #22c55e;
}

.status-dot.offline {
  background: var(--color-text-muted);
}
</style>
