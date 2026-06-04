<script setup lang="ts">
import type { RealTennisTournament } from '@/composables/useRealTennis'

defineProps<{
  tournament: RealTennisTournament
  active: boolean
}>()

defineEmits<{ select: [id: number] }>()
</script>

<template>
  <button
    class="tournament-card"
    :class="{ active }"
    @click="$emit('select', tournament.id)"
  >
    <div class="tournament-name">{{ tournament.name }}</div>
    <div class="tournament-meta">
      <span class="category-badge">{{ tournament.category }}</span>
      <span v-if="tournament.round" class="round-label">{{ tournament.round }}</span>
    </div>
    <div class="match-count">
      {{ tournament.match_count }} match{{ tournament.match_count !== 1 ? 'es' : '' }}
    </div>
  </button>
</template>

<style scoped>
.tournament-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-2) var(--space-3);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all var(--transition-base);
  white-space: nowrap;
  gap: 2px;
  min-width: 120px;
}

.tournament-card:hover {
  border-color: var(--color-brand-primary);
  box-shadow: var(--shadow-md);
}

.tournament-card.active {
  border-color: var(--color-brand-primary);
  background: var(--color-bg-secondary);
}

.tournament-name {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.tournament-meta {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.category-badge {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-brand-live);
}

.round-label {
  font-size: 0.65rem;
  color: var(--color-text-muted);
  font-weight: 600;
}

.match-count {
  font-size: 0.65rem;
  color: var(--color-text-secondary);
  font-weight: 600;
}
</style>
