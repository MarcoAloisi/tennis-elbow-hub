<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'

const CONSENT_KEY = 'cookie_consent'
const visible = ref(false)

onMounted(() => {
  const consent = localStorage.getItem(CONSENT_KEY)
  if (!consent) {
    visible.value = true
  }
})

const acceptAll = () => {
  localStorage.setItem(CONSENT_KEY, 'accepted')
  visible.value = false
}

const rejectNonEssential = () => {
  localStorage.setItem(CONSENT_KEY, 'rejected')
  visible.value = false

  // Disable Google Analytics
  window['ga-disable-G-XXXXXXXXXX'] = true

  // Remove GA cookies
  document.cookie.split(';').forEach((c) => {
    const name = c.trim().split('=')[0]
    if (name.startsWith('_ga') || name.startsWith('_gid')) {
      document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;domain=.${window.location.hostname}`
      document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/`
    }
  })
}
</script>

<template>
  <Transition name="consent-slide">
    <div v-if="visible" class="cookie-consent" role="dialog" aria-label="Cookie consent">
      <div class="consent-content">
        <div class="consent-text">
          <span class="consent-icon">🍪</span>
          <p>
            We use cookies for analytics (Google Analytics) and advertising (Google AdSense)
            to improve your experience. See our
            <RouterLink to="/privacy-policy">Privacy Policy</RouterLink> for details.
          </p>
        </div>
        <div class="consent-actions">
          <button class="btn-reject" @click="rejectNonEssential">
            Essential Only
          </button>
          <button class="btn-accept" @click="acceptAll">
            Accept All
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.cookie-consent {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
  padding: var(--space-4) var(--space-6);
}

.consent-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
}

.consent-text {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}

.consent-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.consent-text p {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin: 0;
}

.consent-text a {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
}

.consent-text a:hover {
  text-decoration: underline;
}

.consent-actions {
  display: flex;
  gap: var(--space-3);
  flex-shrink: 0;
}

.btn-accept,
.btn-reject {
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
  white-space: nowrap;
}

.btn-accept {
  background: var(--color-accent);
  color: #fff;
}

.btn-accept:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
}

.btn-reject {
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.btn-reject:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

/* Slide animation */
.consent-slide-enter-active {
  transition: transform 0.4s ease-out, opacity 0.3s ease-out;
}
.consent-slide-leave-active {
  transition: transform 0.3s ease-in, opacity 0.2s ease-in;
}
.consent-slide-enter-from {
  transform: translateY(100%);
  opacity: 0;
}
.consent-slide-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

@media (max-width: 768px) {
  .consent-content {
    flex-direction: column;
    text-align: center;
    gap: var(--space-4);
  }

  .consent-text {
    flex-direction: column;
  }

  .consent-actions {
    width: 100%;
    justify-content: center;
  }
}
</style>
