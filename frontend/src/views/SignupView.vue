<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Join Tennis Elbow Hub</h1>

      <form @submit.prevent="handleSignup">
        <div class="field">
          <label>Display Name</label>
          <input v-model="displayName" type="text" required placeholder="Your name" />
        </div>
        <div class="field">
          <label>Email</label>
          <input v-model="email" type="email" required placeholder="you@email.com" />
        </div>
        <div class="field">
          <label>Password</label>
          <input v-model="password" type="password" required placeholder="Min 6 characters" minlength="6" />
        </div>

        <p v-if="authStore.error" class="error">{{ authStore.error }}</p>
        <p v-if="success" class="success">Account created! Check your email to confirm.</p>

        <button type="submit" :disabled="authStore.loading">
          {{ authStore.loading ? 'Creating account...' : 'Sign Up' }}
        </button>
      </form>

      <div class="auth-links">
        <router-link to="/login" class="auth-link">Already have an account? Log in</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const displayName = ref('')
const email = ref('')
const password = ref('')
const success = ref(false)

async function handleSignup() {
  success.value = false
  try {
    await authStore.register(email.value, password.value, displayName.value)
    success.value = true
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
h1 {
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
  text-align: center;
}
.field {
  margin-bottom: 1rem;
}
.field label {
  display: block;
  margin-bottom: 4px;
  font-size: 14px;
  color: var(--color-text-secondary);
}
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
.auth-links { margin-top: 16px; text-align: center; }
.auth-link { color: var(--color-brand-primary); font-size: 14px; text-decoration: none; }
</style>
