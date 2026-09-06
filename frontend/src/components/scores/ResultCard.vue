<script setup lang="ts">
import { computed } from 'vue'
import type { ResultEntry } from '@/composables/useResults'

const props = defineProps<{ result: ResultEntry }>()

const players = computed<[string, string] | null>(() => {
  const parts = props.result.match_name.split(' vs ')
  return parts.length === 2 ? [parts[0].trim(), parts[1].trim()] : null
})
</script>

<template>
  <div class="result-card">
    <div class="result-players">
      <template v-if="players">
        <span :class="{ winner: result.winner === players[0] }">{{ players[0] }}</span>
        <span class="vs">vs</span>
        <span :class="{ winner: result.winner === players[1] }">{{ players[1] }}</span>
      </template>
      <span v-else>{{ result.match_name }}</span>
    </div>

    <div class="result-meta">
      <span v-if="result.score" class="result-score">{{ result.score }}</span>
      <span v-if="result.surface" class="footer-tag">{{ result.surface }}</span>
      <span v-if="result.mod" class="footer-tag mod-tag">{{ result.mod }}</span>
      <span v-if="result.p1_elo || result.p2_elo" class="footer-tag">
        {{ result.p1_elo ?? '?' }} / {{ result.p2_elo ?? '?' }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.result-card {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.result-players {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.result-players .winner {
  color: var(--color-text-primary);
  font-weight: 700;
}

.vs {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: 400;
  text-transform: uppercase;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.result-score {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.footer-tag {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  background: var(--color-bg-secondary);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.mod-tag {
  color: var(--color-text-primary);
  text-transform: uppercase;
}
</style>
