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
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all var(--transition-fast);
  overflow: hidden;
}

.theme-toggle:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-hover);
  transform: scale(1.05);
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
  font-size: 1.25rem;
  transition: all var(--transition-base);
}

.sun {
  opacity: 1;
  transform: rotate(0deg);
}

.moon {
  opacity: 0;
  transform: rotate(-90deg);
}

.theme-icon.is-dark .sun {
  opacity: 0;
  transform: rotate(90deg);
}

.theme-icon.is-dark .moon {
  opacity: 1;
  transform: rotate(0deg);
}
</style>
