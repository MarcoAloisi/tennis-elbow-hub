<script setup>
import { useTheme } from '@/composables/useTheme'

const { theme, toggleTheme } = useTheme()
</script>

<template>
  <button 
    class="theme-toggle" 
    @click="toggleTheme"
    :title="theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'"
    aria-label="Toggle theme"
  >
    <span class="theme-icon" :class="{ 'is-dark': theme === 'dark' }">
      <span class="sun">☀️</span>
      <span class="moon">🌙</span>
    </span>
  </button>
</template>

<style scoped>
.theme-toggle {
  position: relative;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
}

.theme-toggle:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.theme-toggle:active {
  transform: scale(0.95);
}

.theme-icon {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  transition: transform var(--transition-base);
}

.sun, .moon {
  position: absolute;
  top: 50%;
  left: 50%;
  font-size: 1.25rem;
  transition: all var(--transition-base);
  line-height: 1;
  display: flex;
}

.sun {
  opacity: 1;
  transform: translate(-50%, -50%) rotate(0deg);
}

.moon {
  opacity: 0;
  transform: translate(-50%, -50%) rotate(-90deg);
}

.theme-icon.is-dark .sun {
  opacity: 0;
  transform: translate(-50%, -50%) rotate(90deg);
}

.theme-icon.is-dark .moon {
  opacity: 1;
  transform: translate(-50%, -50%) rotate(0deg);
}
</style>
