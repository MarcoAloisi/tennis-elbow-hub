<script setup lang="ts">
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
          <p>
            We use cookies for analytics (Google Analytics) and advertising (Google AdSense)
            to improve your experience. See our
            <RouterLink to="/privacy-policy">Privacy Policy</RouterLink> for details.
          </p>
        </div>
        <div class="consent-actions">
          <button class="btn-reject" @click="rejectNonEssential">
            Essential only
          </button>
          <button class="btn-accept" @click="acceptAll">
            Accept all
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
  background: var(--color-bg-secondary);
  padding: var(--space-3) var(--space-6);
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
  flex: 1;
}

.consent-text p {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin: 0;
}

.consent-text a {
  color: var(--color-text-primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.consent-actions {
  display: flex;
  gap: var(--space-2);
  flex-shrink: 0;
}

.btn-accept,
.btn-reject {
  min-height: 40px;
  padding: 0 var(--space-5);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast), transform 100ms;
  white-space: nowrap;
}

.btn-accept:active,
.btn-reject:active {
  transform: translateY(1px);
}

.btn-accept {
  background: var(--color-brand-primary);
  color: var(--color-text-inverse);
}

.btn-accept:hover {
  filter: brightness(1.08);
}

.btn-reject {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.btn-reject:hover {
  filter: brightness(1.15);
}

.consent-slide-enter-active,
.consent-slide-leave-active {
  transition: transform 0.3s cubic-bezier(0.23, 1, 0.32, 1), opacity 0.2s;
}
.consent-slide-enter-from,
.consent-slide-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

@media (max-width: 768px) {
  .cookie-consent {
    padding: var(--space-3) var(--space-4);
  }

  .consent-content {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-3);
  }

  .consent-actions {
    width: 100%;
  }

  .btn-accept,
  .btn-reject {
    flex: 1;
  }
}
</style>
