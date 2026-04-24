<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { apiUrl } from '@/config/api'
import { supabase } from '@/config/supabase'
import { Clock, RefreshCw, LogOut } from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()
const checking = ref(false)
const message = ref('')

async function checkStatus() {
  checking.value = true
  message.value = ''
  try {
    const { data } = await supabase.auth.getSession()
    const res = await fetch(apiUrl('/api/profile/me'), {
      headers: { Authorization: `Bearer ${data.session?.access_token}` },
    })
    if (!res.ok) throw new Error()
    const profile = await res.json()
    if (profile.approved) {
      router.push('/')
    } else {
      message.value = 'Still pending — check back later.'
    }
  } catch {
    message.value = 'Could not reach server. Try again.'
  } finally {
    checking.value = false
  }
}
</script>

<template>
  <div class="pending-page">
    <div class="pending-card">
      <div class="icon-wrap">
        <Clock :size="40" />
      </div>
      <h1>Account pending approval</h1>
      <p class="sub">
        Your account is waiting for admin approval. You'll be able to access
        the site once an admin reviews your signup.
      </p>
      <p v-if="message" class="status-msg">{{ message }}</p>
      <div class="actions">
        <button class="btn btn-primary" @click="checkStatus" :disabled="checking">
          <RefreshCw :size="15" :class="{ spinning: checking }" />
          Check status
        </button>
        <button class="btn btn-secondary" @click="authStore.logout().then(() => router.push('/login'))">
          <LogOut :size="15" /> Log out
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pending-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

.pending-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-10) var(--space-8);
  max-width: 420px;
  width: 100%;
  text-align: center;
  box-shadow: var(--shadow-lg);
}

.icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
  margin-bottom: var(--space-5);
}

h1 {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3) 0;
}

.sub {
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
  line-height: 1.6;
  margin: 0 0 var(--space-5) 0;
}

.status-msg {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-4) 0;
}

.actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
  flex-wrap: wrap;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
.spinning {
  animation: spin 0.8s linear infinite;
}
</style>
