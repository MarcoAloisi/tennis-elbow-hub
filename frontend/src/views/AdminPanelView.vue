<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { supabase } from '@/config/supabase'
import { apiUrl } from '@/config/api'
import { Shield, Check, X, RefreshCw, User } from 'lucide-vue-next'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'

interface PendingVerification {
  user_id: string
  display_name: string | null
  in_game_name: string | null
  player_name: string
  created_at: string
}

const verifications = ref<PendingVerification[]>([])
const isLoading = ref(false)
const error = ref('')
const actionLoading = ref<string | null>(null)
const successMessage = ref('')

async function getAuthHeaders() {
  const { data } = await supabase.auth.getSession()
  return { Authorization: `Bearer ${data.session?.access_token}` }
}

async function fetchVerifications() {
  isLoading.value = true
  error.value = ''
  try {
    const headers = await getAuthHeaders()
    const res = await fetch(apiUrl('/api/admin/profile-verifications'), { headers })
    if (!res.ok) throw new Error(`Failed to load verifications (${res.status})`)
    verifications.value = await res.json()
  } catch (e: any) {
    error.value = e.message || 'Failed to load pending verifications.'
  } finally {
    isLoading.value = false
  }
}

async function approve(userId: string) {
  actionLoading.value = userId
  error.value = ''
  try {
    const headers = await getAuthHeaders()
    const res = await fetch(apiUrl(`/api/admin/profile-verifications/${userId}/approve`), {
      method: 'POST',
      headers,
    })
    if (!res.ok) throw new Error(`Approve failed (${res.status})`)
    verifications.value = verifications.value.filter(v => v.user_id !== userId)
    successMessage.value = 'Player link approved.'
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (e: any) {
    error.value = e.message || 'Failed to approve.'
  } finally {
    actionLoading.value = null
  }
}

async function reject(userId: string) {
  actionLoading.value = userId
  error.value = ''
  try {
    const headers = await getAuthHeaders()
    const res = await fetch(apiUrl(`/api/admin/profile-verifications/${userId}/reject`), {
      method: 'POST',
      headers,
    })
    if (!res.ok) throw new Error(`Reject failed (${res.status})`)
    verifications.value = verifications.value.filter(v => v.user_id !== userId)
    successMessage.value = 'Player link rejected.'
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (e: any) {
    error.value = e.message || 'Failed to reject.'
  } finally {
    actionLoading.value = null
  }
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

onMounted(fetchVerifications)
</script>

<template>
  <div class="admin-panel">
    <div class="panel-header">
      <div class="panel-title">
        <Shield :size="24" class="title-icon" />
        <h1>Admin Panel</h1>
      </div>
      <button class="btn-refresh" @click="fetchVerifications" :disabled="isLoading" title="Refresh">
        <RefreshCw :size="16" :class="{ spinning: isLoading }" />
        Refresh
      </button>
    </div>

    <ErrorAlert v-if="error" :message="error" @dismiss="error = ''" />

    <div v-if="successMessage" class="success-banner">{{ successMessage }}</div>

    <section class="panel-section">
      <h2 class="section-title">
        Pending Player Link Verifications
        <span class="badge" v-if="!isLoading">{{ verifications.length }}</span>
      </h2>

      <LoadingSpinner v-if="isLoading" />

      <div v-else-if="verifications.length === 0" class="empty-state">
        <Check :size="40" class="empty-icon" />
        <p>No pending verifications</p>
      </div>

      <div v-else class="verifications-list">
        <div
          v-for="v in verifications"
          :key="v.user_id"
          class="verification-card"
        >
          <div class="card-info">
            <div class="user-icon-wrap">
              <User :size="20" />
            </div>
            <div class="card-details">
              <span class="display-name">{{ v.display_name || 'Unnamed user' }}</span>
              <span class="meta">In-game name: <strong>{{ v.in_game_name || '—' }}</strong></span>
              <span class="meta">Claiming player: <strong class="player-claim">{{ v.player_name }}</strong></span>
              <span class="meta date">Requested {{ formatDate(v.created_at) }}</span>
            </div>
          </div>
          <div class="card-actions">
            <button
              class="btn-approve"
              @click="approve(v.user_id)"
              :disabled="actionLoading === v.user_id"
              title="Approve player link"
            >
              <Check :size="16" /> Approve
            </button>
            <button
              class="btn-reject"
              @click="reject(v.user_id)"
              :disabled="actionLoading === v.user_id"
              title="Reject player link"
            >
              <X :size="16" /> Reject
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.admin-panel {
  max-width: 800px;
  margin: 0 auto;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-6);
  flex-wrap: wrap;
  gap: var(--space-3);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.panel-title h1 {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.title-icon {
  color: #6366f1;
}

.btn-refresh {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-refresh:hover:not(:disabled) {
  color: var(--color-text-primary);
  border-color: var(--color-accent);
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spinning {
  animation: spin 0.8s linear infinite;
}

.success-banner {
  background: var(--color-success-light, rgba(34, 197, 94, 0.1));
  border: 1px solid var(--color-success, #22c55e);
  color: var(--color-success, #22c55e);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.panel-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-5) 0;
}

.badge {
  background: #6366f1;
  color: white;
  font-size: var(--font-size-xs);
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  min-width: 22px;
  text-align: center;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-8) 0;
  color: var(--color-text-muted);
}

.empty-icon {
  color: #22c55e;
  opacity: 0.6;
}

.verifications-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.verification-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  flex-wrap: wrap;
}

.card-info {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  flex: 1;
  min-width: 200px;
}

.user-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(99, 102, 241, 0.15);
  color: #6366f1;
  flex-shrink: 0;
}

.card-details {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.display-name {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.meta {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.player-claim {
  color: #6366f1;
}

.date {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.card-actions {
  display: flex;
  gap: var(--space-2);
  flex-shrink: 0;
}

.btn-approve,
.btn-reject {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
}

.btn-approve {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.btn-approve:hover:not(:disabled) {
  background: rgba(34, 197, 94, 0.25);
}

.btn-reject {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.btn-reject:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.25);
}

.btn-approve:disabled,
.btn-reject:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
