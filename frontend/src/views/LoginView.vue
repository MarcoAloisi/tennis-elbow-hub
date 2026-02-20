<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

const handleLogin = async () => {
  if (!email.value || !password.value) return
  
  isSubmitting.value = true
  errorMessage.value = ''
  
  try {
    await authStore.login(email.value, password.value)
    // Redirect to home or wherever they came from
    router.push('/')
  } catch (error) {
    errorMessage.value = error.message || 'Failed to sign in. Please check your credentials.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <h1>Welcome Back</h1>
        <p>Sign in to your Tennis Elbow Hub account</p>
      </div>

      <form @submit.prevent="handleLogin" class="auth-form">
        <div class="form-group">
          <label for="email">Email Address</label>
          <input 
            type="email" 
            id="email" 
            v-model="email" 
            required 
            placeholder="player@example.com"
            :disabled="isSubmitting"
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input 
            type="password" 
            id="password" 
            v-model="password" 
            required 
            placeholder="••••••••"
            :disabled="isSubmitting"
          />
        </div>

        <div v-if="errorMessage" class="error-alert">
          {{ errorMessage }}
        </div>

        <button type="submit" class="btn-primary btn-block" :disabled="isSubmitting">
          <span v-if="isSubmitting">Signing in...</span>
          <span v-else>Sign In</span>
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 200px);
  padding: var(--space-4);
}

.auth-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-10) var(--space-8);
  width: 100%;
  max-width: 440px;
  box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.auth-header {
  text-align: center;
}

.auth-header h1 {
  font-family: var(--font-heading);
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.auth-header p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-family: var(--font-body);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

label {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--color-text-primary);
}

input {
  background: var(--color-background);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  font-family: var(--font-body);
  font-size: var(--font-size-md);
  transition: all var(--transition-base);
}

input:focus {
  outline: none;
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 1px var(--color-brand-primary);
}

input::placeholder {
  color: var(--color-text-secondary);
  opacity: 0.5;
}

input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-alert {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.2);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  text-align: center;
}

.btn-primary {
  background: var(--color-brand-primary);
  color: var(--color-bg-primary); /* Dark text on neon bg */
  border: none;
  padding: 12px 24px;
  border-radius: var(--radius-md);
  font-family: var(--font-heading);
  font-weight: 800;
  font-size: var(--font-size-md);
  cursor: pointer;
  transition: all var(--transition-base);
  margin-top: var(--space-2);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-brand-accent);
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.btn-block {
  width: 100%;
}
</style>


