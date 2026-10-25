<script setup lang="ts">
import { ref, onMounted } from 'vue'

const DISMISSED_KEY = 'ig_cta_dismissed'
const visible = ref(false)

const SHOW_AFTER_MS = 30000

// Wait until the visitor has settled in and answered the cookie banner, so the
// first screen carries one overlay at most.
onMounted(() => {
  if (sessionStorage.getItem(DISMISSED_KEY)) return
  setTimeout(() => {
    if (localStorage.getItem('cookie_consent')) visible.value = true
  }, SHOW_AFTER_MS)
})

function dismiss() {
  sessionStorage.setItem(DISMISSED_KEY, '1')
  visible.value = false
}
</script>

<template>
  <Transition name="ig-slide">
    <div v-if="visible" class="ig-cta" role="complementary" aria-label="Follow on Instagram">
      <button class="ig-close" @click="dismiss" aria-label="Dismiss">×</button>
      <div class="ig-body">
        <svg class="ig-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="2" y="2" width="20" height="20" rx="5" fill="#dc2743" />
          <circle cx="12" cy="12" r="4.5" fill="none" stroke="white" stroke-width="2" />
          <circle cx="17" cy="7" r="1.2" fill="white" />
        </svg>
        <div class="ig-text">
          <p class="ig-title">Follow us on Instagram</p>
          <p class="ig-handle">@te4__tv, videos and content</p>
        </div>
      </div>
      <a
        href="https://www.instagram.com/te4__tv/"
        target="_blank"
        rel="noopener noreferrer"
        class="ig-btn"
        @click="dismiss"
      >
        Follow
      </a>
    </div>
  </Transition>
</template>

<style scoped>
.ig-cta {
  position: fixed;
  bottom: var(--space-6);
  left: var(--space-6);
  z-index: 9000;
  width: 270px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ig-close {
  position: absolute;
  top: var(--space-1);
  right: var(--space-1);
  width: 32px;
  height: 32px;
  background: none;
  color: var(--color-text-muted);
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: color var(--transition-fast);
}

.ig-close:hover {
  color: var(--color-text-primary);
}

.ig-body {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding-right: var(--space-4);
}

.ig-icon {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
}

.ig-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ig-title {
  margin: 0;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.ig-handle {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.ig-btn {
  display: grid;
  place-items: center;
  min-height: 40px;
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  border-radius: var(--radius-md);
  transition: filter var(--transition-fast), transform 100ms;
}

.ig-btn:hover {
  color: var(--color-text-primary);
  filter: brightness(1.15);
}

.ig-btn:active {
  transform: translateY(1px);
}

.ig-slide-enter-active,
.ig-slide-leave-active {
  transition: transform 0.3s cubic-bezier(0.23, 1, 0.32, 1), opacity 0.2s;
}
.ig-slide-enter-from,
.ig-slide-leave-to {
  transform: translateY(120%);
  opacity: 0;
}

@media (max-width: 480px) {
  .ig-cta {
    left: var(--space-3);
    right: var(--space-3);
    bottom: var(--space-3);
    width: auto;
  }
}
</style>
