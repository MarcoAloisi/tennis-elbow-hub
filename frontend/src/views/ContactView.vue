<script setup>
import { ref, computed } from 'vue'
import { apiUrl } from '../config/api'

const form = ref({
  name: '',
  discord: '',
  message: ''
})

const status = ref('idle') // idle | sending | success | error
const errorMsg = ref('')

const isValid = computed(() => {
  return (
    form.value.name.trim().length >= 1 &&
    form.value.discord.trim().length >= 2 &&
    form.value.message.trim().length >= 10
  )
})

const charsRemaining = computed(() => 2000 - form.value.message.length)

const submit = async () => {
  if (!isValid.value || status.value === 'sending') return

  status.value = 'sending'
  errorMsg.value = ''

  try {
    const response = await fetch(apiUrl('/api/contact/send'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: form.value.name.trim(),
        discord: form.value.discord.trim(),
        message: form.value.message.trim()
      })
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || 'Failed to send message')
    }

    status.value = 'success'
    form.value = { name: '', discord: '', message: '' }
  } catch (err) {
    status.value = 'error'
    errorMsg.value =
      err.message ||
      'Something went wrong. Please try again or reach out on Discord.'
  }
}

const resetForm = () => {
  status.value = 'idle'
  errorMsg.value = ''
}
</script>

<template>
  <div class="contact-view">
    <div class="contact-content">
      <h1>Contact Us</h1>
      <p class="contact-subtitle">
        Have a question, suggestion, or issue? Fill out the form below and we'll get back to you.
        You can also reach us on the
        <a href="https://discord.com/invite/PY7hZXZcF6" target="_blank" rel="noopener noreferrer">
          Tennis Elbow 4 Tour Discord</a>.
      </p>

      <!-- Success State -->
      <div v-if="status === 'success'" class="success-card">
        <div class="success-icon">✅</div>
        <h2>Message Sent!</h2>
        <p>Thanks for reaching out. We'll get back to you as soon as possible.</p>
        <button class="btn-primary" @click="resetForm">Send Another Message</button>
      </div>

      <!-- Form -->
      <form v-else class="contact-form" @submit.prevent="submit">
        <div class="form-group">
          <label for="contact-name">Name <span class="required">*</span></label>
          <input
            id="contact-name"
            v-model="form.name"
            type="text"
            placeholder="Your name"
            maxlength="100"
            required
          />
        </div>

        <div class="form-group">
          <label for="contact-discord">Discord Tag <span class="required">*</span></label>
          <input
            id="contact-discord"
            v-model="form.discord"
            type="text"
            placeholder="e.g. username#1234 or @username"
            maxlength="100"
            required
          />
          <span class="field-hint">So we can reach you back on Discord</span>
        </div>

        <div class="form-group">
          <label for="contact-message">Message <span class="required">*</span></label>
          <textarea
            id="contact-message"
            v-model="form.message"
            placeholder="What would you like to tell us? (min 10 characters)"
            maxlength="2000"
            rows="6"
            required
          ></textarea>
          <span class="field-hint" :class="{ 'char-warn': charsRemaining < 100 }">
            {{ charsRemaining }} characters remaining
          </span>
        </div>

        <div v-if="status === 'error'" class="error-msg">
          {{ errorMsg }}
        </div>

        <button
          type="submit"
          class="btn-submit"
          :class="{ loading: status === 'sending' }"
          :disabled="!isValid || status === 'sending'"
        >
          <span v-if="status === 'sending'" class="spinner"></span>
          {{ status === 'sending' ? 'Sending...' : 'Send Message' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.contact-view {
  min-height: 100%;
  max-width: 640px;
  margin: 0 auto;
  padding-bottom: var(--space-12);
}

.contact-content {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8) var(--space-10);
}

h1 {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.contact-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: var(--space-8);
  padding-bottom: var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.contact-subtitle a {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
}

.contact-subtitle a:hover {
  text-decoration: underline;
}

/* Form */
.contact-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-group label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.required {
  color: #ef4444;
}

.form-group input,
.form-group textarea {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-family: inherit;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  outline: none;
}

.form-group input:focus,
.form-group textarea:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
}

.form-group input::placeholder,
.form-group textarea::placeholder {
  color: var(--color-text-muted);
}

.form-group textarea {
  resize: vertical;
  min-height: 120px;
}

.field-hint {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.field-hint.char-warn {
  color: #ef4444;
}

/* Buttons */
.btn-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all var(--transition-fast);
  width: 100%;
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.3);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-submit.loading {
  opacity: 0.8;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  padding: var(--space-3) var(--space-6);
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.3);
}

/* Success */
.success-card {
  text-align: center;
  padding: var(--space-8) 0;
}

.success-icon {
  font-size: 3rem;
  margin-bottom: var(--space-4);
}

.success-card h2 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.success-card p {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-6);
}

/* Error */
.error-msg {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  font-size: var(--font-size-sm);
  color: #ef4444;
}

@media (max-width: 768px) {
  .contact-content {
    padding: var(--space-6);
  }

  h1 {
    font-size: var(--font-size-2xl);
  }
}
</style>
