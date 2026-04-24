<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { supabase } from '@/config/supabase'
import { apiUrl } from '@/config/api'
import { clearApprovalCache } from '@/router'
import { Shield, Check, X, RefreshCw, User, UserCheck } from 'lucide-vue-next'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'

interface PendingVerification {
  user_id: string
  display_name: string | null
  in_game_name: string | null
  player_name: string
  created_at: string
}

interface PendingSignup {
  user_id: string
  display_name: string | null
  in_game_name: string | null
  created_at: string
}

const verifications = ref<PendingVerification[]>([])
const signups = ref<PendingSignup[]>([])
const isLoading = ref(false)
const error = ref('')
const actionLoading = ref<string | null>(null)
const successMessage = ref('')

async function getAuthHeaders() {
  const { data } = await supabase.auth.getSession()
  return { Authorization: `Bearer ${data.session?.access_token}` }
}

async function fetchAll() {
  isLoading.value = true
  error.value = ''
  try {
    const headers = await getAuthHeaders()
    const [verRes, signupRes] = await Promise.all([
      fetch(apiUrl('/api/admin/profile-verifications'), { headers }),
      fetch(apiUrl('/api/admin/pending-signups'), { headers }),
    ])
    if (!verRes.ok) throw new Error(`Failed to load verifications (${verRes.status})`)
    if (!signupRes.ok) throw new Error(`Failed to load pending signups (${signupRes.status})`)
    verifications.value = await verRes.json()
    signups.value = await signupRes.json()
  } catch (e: any) {
    error.value = e.message || 'Failed to load data.'
  } finally {
    isLoading.value = false
  }
}

async function approveVerification(userId: string) {
  actionLoading.value = userId
  error.value = ''
  try {
    const headers = await getAuthHeaders()
    const res = await fetch(apiUrl(`/api/admin/profile-verifications/${userId}/approve`), { method: 'POST', headers })
    if (!res.ok) throw new Error(`Approve failed (${res.status})`)
    verifications.value = verifications.value.filter(v => v.user_id !== userId)
    flash('Player link approved.')
  } catch (e: any) {
    error.value = e.message || 'Failed to approve.'
  } finally {
    actionLoading.value = null
  }
}

async function rejectVerification(userId: string) {
  actionLoading.value = userId
  error.value = ''
  try {
    const headers = await getAuthHeaders()
    const res = await fetch(apiUrl(`/api/admin/profile-verifications/${userId}/reject`), { method: 'POST', headers })
    if (!res.ok) throw new Error(`Reject failed (${res.status})`)
    verifications.value = verifications.value.filter(v => v.user_id !== userId)
    flash('Player link rejected.')
  } catch (e: any) {
    error.value = e.message || 'Failed to reject.'
  } finally {
    actionLoading.value = null
  }
}

async function approveSignup(userId: string) {
  actionLoading.value = userId
  error.value = ''
  try {
    const headers = await getAuthHeaders()
    const res = await fetch(apiUrl(`/api/admin/pending-signups/${userId}/approve`), { method: 'POST', headers })
    if (!res.ok) throw new Error(`Approve failed (${res.status})`)
    signups.value = signups.value.filter(s => s.user_id !== userId)
    clearApprovalCache()
    flash('User approved. They can now access the site.')
  } catch (e: any) {
    error.value = e.message || 'Failed to approve.'
  } finally {
    actionLoading.value = null
  }
}

function flash(msg: string) {
  successMessage.value = msg
  setTimeout(() => { successMessage.value = '' }, 4000)
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

onMounted(fetchAll)
</script>

<template>
  <div class="admin-panel">
    <div class="panel-header">
      <div class="panel-title">
        <Shield :size="24" class="title-icon" />
        <h1>Admin Panel</h1>
      </div>
      <button class="btn-refresh" @click="fetchAll" :disabled="isLoading" title="Refresh">
        <RefreshCw :size="16" :class="{ spinning: isLoading }" />
        Refresh
      </button>
    </div>

    <ErrorAlert v-if="error" :message="error" @dismiss="error = ''" />
    <div v-if="successMessage" class="success-banner">{{ successMessage }}</div>

    <!-- Pending Signups -->
    <section class="panel-section">
      <h2 class="section-title">
        <UserCheck :size="20" />
        Pending Signup Approvals
        <span class="badge badge--orange" v-if="!isLoading">{{ signups.length }}</span>
      </h2>

      <LoadingSpinner v-if="isLoading" />

      <div v-else-if="signups.length === 0" class="empty-state">
        <Check :size="36" class="empty-icon" />
        <p>No pending signups</p>
      </div>

      <div v-else class="card-list">
        <div v-for="s in signups" :key="s.user_id" class="item-card">
          <div class="card-info">
            <div class="user-icon-wrap user-icon-wrap--orange">
              <User :size="18" />
            </div>
            <div class="card-details">
              <span class="display-name">{{ s.display_name || 'Unnamed user' }}</span>
              <span class="meta">In-game name: <strong>{{ s.in_game_name || '—' }}</strong></span>
              <span class="meta date">Signed up {{ formatDate(s.created_at) }}</span>
            </div>
          </div>
          <div class="card-actions">
            <button class="btn-approve" @click="approveSignup(s.user_id)" :disabled="actionLoading === s.user_id">
              <Check :size="15" /> Approve
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Player Link Verifications -->
    <section class="panel-section" style="margin-top: var(--space-6)">
      <h2 class="section-title">
        <Shield :size="20" />
        Pending Player Link Verifications
        <span class="badge" v-if="!isLoading">{{ verifications.length }}</span>
      </h2>

      <LoadingSpinner v-if="isLoading" />

      <div v-else-if="verifications.length === 0" class="empty-state">
        <Check :size="36" class="empty-icon" />
        <p>No pending verifications</p>
      </div>

      <div v-else class="card-list">
        <div v-for="v in verifications" :key="v.user_id" class="item-card">
          <div class="card-info">
            <div class="user-icon-wrap">
              <User :size="18" />
            </div>
            <div class="card-details">
              <span class="display-name">{{ v.display_name || 'Unnamed user' }}</span>
              <span class="meta">In-game name: <strong>{{ v.in_game_name || '—' }}</strong></span>
              <span class="meta">Claiming player: <strong class="player-claim">{{ v.player_name }}</strong></span>
              <span class="meta date">Requested {{ formatDate(v.created_at) }}</span>
            </div>
          </div>
          <div class="card-actions">
            <button class="btn-approve" @click="approveVerification(v.user_id)" :disabled="actionLoading === v.user_id">
              <Check :size="15" /> Approve
            </button>
            <button class="btn-reject" @click="rejectVerification(v.user_id)" :disabled="actionLoading === v.user_id">
              <X :size="15" /> Reject
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

.title-icon { color: #6366f1; }

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

.btn-refresh:hover:not(:disabled) { color: var(--color-text-primary); border-color: var(--color-accent); }
.btn-refresh:disabled { opacity: 0.5; cursor: not-allowed; }

@keyframes spin { to { transform: rotate(360deg); } }
.spinning { animation: spin 0.8s linear infinite; }

.success-banner {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid #22c55e;
  color: #22c55e;
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
  gap: var(--space-2);
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
}

.badge--orange {
  background: #f59e0b;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-6) 0;
  color: var(--color-text-muted);
}

.empty-icon { color: #22c55e; opacity: 0.6; }

.card-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.item-card {
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
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: rgba(99, 102, 241, 0.12);
  color: #6366f1;
  flex-shrink: 0;
}

.user-icon-wrap--orange {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}

.card-details { display: flex; flex-direction: column; gap: 2px; }

.display-name { font-weight: 600; color: var(--color-text-primary); font-size: var(--font-size-base); }

.meta { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.player-claim { color: #6366f1; }
.date { color: var(--color-text-muted); font-size: var(--font-size-xs); }

.card-actions { display: flex; gap: var(--space-2); flex-shrink: 0; }

.btn-approve, .btn-reject {
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

.btn-approve { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
.btn-approve:hover:not(:disabled) { background: rgba(34, 197, 94, 0.25); }
.btn-reject { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.btn-reject:hover:not(:disabled) { background: rgba(239, 68, 68, 0.25); }
.btn-approve:disabled, .btn-reject:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
