<script setup lang="ts">
import { ref, onMounted } from 'vue'

const DISMISSED_KEY = 'ig_cta_dismissed'
const visible = ref(false)

onMounted(() => {
  if (!sessionStorage.getItem(DISMISSED_KEY)) {
    visible.value = true
  }
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
          <defs>
            <linearGradient id="ig-cta-gradient" x1="0%" y1="100%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#f09433" />
              <stop offset="25%" stop-color="#e6683c" />
              <stop offset="50%" stop-color="#dc2743" />
              <stop offset="75%" stop-color="#cc2366" />
              <stop offset="100%" stop-color="#bc1888" />
            </linearGradient>
          </defs>
          <rect x="2" y="2" width="20" height="20" rx="5" fill="url(#ig-cta-gradient)" />
          <circle cx="12" cy="12" r="4.5" fill="none" stroke="white" stroke-width="2" />
          <circle cx="17" cy="7" r="1.2" fill="white" />
        </svg>
        <div class="ig-text">
          <p class="ig-title">Follow us on Instagram</p>
          <p class="ig-handle">@te4__tv — videos &amp; content</p>
        </div>
      </div>
      <a
        href="https://www.instagram.com/te4__tv/"
        target="_blank"
        rel="noopener noreferrer"
        class="ig-btn"
        @click="dismiss"
      >
        Follow →
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
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ig-close {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  padding: var(--space-1);
  border-radius: var(--radius-sm);
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
  width: 40px;
  height: 40px;
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
  color: var(--color-text-muted);
}

.ig-btn {
  display: block;
  text-align: center;
  padding: var(--space-2) var(--space-4);
  background: linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
  color: white;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  border-radius: var(--radius-md);
  text-decoration: none;
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.ig-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Slide-up animation */
.ig-slide-enter-active {
  transition: transform 0.4s ease-out, opacity 0.3s ease-out;
}
.ig-slide-leave-active {
  transition: transform 0.25s ease-in, opacity 0.2s ease-in;
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
