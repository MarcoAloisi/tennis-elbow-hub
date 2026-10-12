<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useHead } from '@unhead/vue'

useHead({ meta: [{ name: 'robots', content: 'noindex' }] })
</script>

<template>
  <div class="not-found-view">
    <p class="code">404</p>
    <h1>Page not found</h1>
    <p class="message">
      That page does not exist or has moved. Try one of these instead.
    </p>
    <nav class="links" aria-label="Useful pages">
      <RouterLink to="/" class="btn btn-primary">Home</RouterLink>
      <RouterLink to="/live" class="btn btn-secondary">Live Scores</RouterLink>
      <RouterLink to="/guides" class="btn btn-secondary">Guides</RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.not-found-view {
  max-width: 560px;
  margin: 0 auto;
  padding: var(--space-16) var(--space-4);
  text-align: center;
}

.code {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-brand-primary);
  margin-bottom: var(--space-2);
}

h1 {
  font-size: var(--font-size-2xl);
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.message {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-6);
}

.links {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
  flex-wrap: wrap;
}
</style>
