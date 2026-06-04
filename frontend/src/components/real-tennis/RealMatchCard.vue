<script setup lang="ts">
import type { RealTennisMatch } from '@/composables/useRealTennis'

const props = defineProps<{ match: RealTennisMatch }>()

function formatTime(ts: number | null): string {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="real-match-card" :class="{ 'is-live': match.status === 'live' }">
    <!-- Header -->
    <div class="match-header">
      <div class="status-badges">
        <span v-if="match.status === 'live'" class="badge badge-live">
          <span class="live-dot-pulse"></span>
          LIVE
        </span>
        <span v-else-if="match.status === 'upcoming'" class="badge badge-waiting">
          {{ formatTime(match.start_timestamp) || 'TBD' }}
        </span>
        <span v-else class="badge badge-finished">✓ Finished</span>

        <span class="badge badge-tournament">{{ match.tournament.name }}</span>
        <span v-if="match.tournament.round" class="badge badge-round">
          {{ match.tournament.round }}
        </span>
      </div>
    </div>

    <!-- Players + scores grid -->
    <div class="match-grid">
      <!-- Player 1 -->
      <div class="player-row">
        <div class="player-info">
          <span class="player-name">{{ match.player1 }}</span>
        </div>
        <div class="sets-column">
          <span
            v-for="(set, i) in match.score.sets"
            :key="i"
            class="set-score"
          >{{ set[0] }}</span>
        </div>
      </div>

      <!-- Player 2 -->
      <div class="player-row">
        <div class="player-info">
          <span class="player-name">{{ match.player2 }}</span>
        </div>
        <div class="sets-column">
          <span
            v-for="(set, i) in match.score.sets"
            :key="i"
            class="set-score"
          >{{ set[1] }}</span>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="match-footer">
      <span class="footer-tag">{{ match.tournament.category }}</span>
    </div>
  </div>
</template>

<style scoped>
.real-match-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  transition: all var(--transition-base);
}

.real-match-card:hover {
  border-color: var(--color-brand-primary);
  box-shadow: var(--shadow-md);
}

.real-match-card.is-live {
  border-left: 4px solid var(--color-brand-live);
}

.match-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-badges {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  flex-wrap: wrap;
}

.badge-live {
  background-color: var(--color-brand-live);
  color: var(--color-text-inverse);
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  font-family: var(--font-heading);
  font-weight: 700;
  font-style: italic;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.live-dot-pulse {
  width: 8px;
  height: 8px;
  background-color: var(--color-surface);
  border-radius: 50%;
  animation: pulse 1.5s infinite ease-in-out;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(255, 255, 255, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0); }
}

.badge-waiting {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-family: var(--font-heading);
  font-weight: 600;
}

.badge-finished {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-muted);
  font-family: var(--font-heading);
  font-weight: 600;
}

.badge-tournament {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 0.75rem;
  max-width: 180px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.badge-round {
  background: var(--color-bg-secondary);
  color: var(--color-text-muted);
  font-size: 0.7rem;
  font-weight: 600;
}

.match-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.player-row {
  display: flex;
  align-items: center;
  min-height: 36px;
}

.player-info {
  flex: 1;
  min-width: 0;
}

.player-name {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.sets-column {
  display: flex;
  gap: 12px;
  margin-left: var(--space-3);
}

.set-score {
  width: 20px;
  text-align: center;
  font-family: var(--font-data);
  font-size: var(--font-size-lg);
  font-weight: 500;
  color: var(--color-text-primary);
}

.match-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-3);
}

.footer-tag {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  background: var(--color-bg-secondary);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
</style>
