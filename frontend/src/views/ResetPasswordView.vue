<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Set New Password</h1>

      <form @submit.prevent="handleReset">
        <div class="field">
          <label>New Password</label>
          <input v-model="password" type="password" required placeholder="Min 6 characters" minlength="6" />
        </div>
        <div class="field">
          <label>Confirm Password</label>
          <input v-model="confirm" type="password" required placeholder="Repeat password" />
        </div>

        <p v-if="mismatch" class="error">Passwords do not match</p>
        <p v-if="authStore.error" class="error">{{ authStore.error }}</p>
        <p v-if="success" class="success">Password updated! Redirecting to login...</p>

        <button type="submit" :disabled="authStore.loading">
          {{ authStore.loading ? 'Updating...' : 'Update Password' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const password = ref('')
const confirm = ref('')
const mismatch = ref(false)
const success = ref(false)

async function handleReset() {
  mismatch.value = false
  if (password.value !== confirm.value) {
    mismatch.value = true
    return
  }
  try {
    await authStore.updatePassword(password.value)
    success.value = true
    setTimeout(() => router.push('/login'), 2000)
  } catch {
    // error shown via authStore.error
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
  padding: 2rem;
}
.auth-card {
  background: var(--color-surface);
  border-radius: 12px;
  padding: 2rem;
  width: 100%;
  max-width: 400px;
  border: 1px solid var(--color-border);
}
h1 { font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center; }
.field { margin-bottom: 1rem; }
.field label { display: block; margin-bottom: 4px; font-size: 14px; color: var(--color-text-secondary); }
.field input {
  width: 100%;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  font-size: 14px;
  box-sizing: border-box;
}
button[type="submit"] {
  width: 100%;
  padding: 12px;
  border-radius: 6px;
  background: var(--color-brand-primary);
  color: var(--color-text-inverse);
  border: none;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
  margin-top: 8px;
}
button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: var(--color-error); font-size: 14px; margin: 8px 0; }
.success { color: var(--color-success); font-size: 14px; margin: 8px 0; }
</style>
