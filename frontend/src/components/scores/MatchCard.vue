<script setup>
import { computed } from 'vue'

const props = defineProps({
  server: {
    type: Object,
    required: true
  }
})

// Parse player names from match_name
const players = computed(() => {
  const name = props.server.match_name || ''
  if (name.includes(' vs ')) {
    const parts = name.split(' vs ')
    return { player1: parts[0].trim(), player2: parts[1].trim() }
  }
  return { player1: name, player2: 'Unknown' }
})

// Parse score for display
const scoreDisplay = computed(() => {
  const score = props.server.score || ''
  // Format: "6/3 4/6 1/1 -- 00:40•"
  const parts = score.split(' -- ')
  const sets = parts[0] ? parts[0].trim().split(' ') : []
  const currentGame = parts[1] ? parts[1].trim() : ''
  return { sets, currentGame }
})

// Surface badge class
const surfaceClass = computed(() => {
  const surface = (props.server.surface_name || '').toLowerCase()
  if (surface.includes('clay')) return 'badge-surface-clay'
  if (surface.includes('grass')) return 'badge-surface-grass'
  if (surface.includes('indoor')) return 'badge-surface-indoor'
  return 'badge-surface-hard'
})

// Format surface name
const surfaceDisplay = computed(() => {
  const name = props.server.surface_name || ''
  const map = {
    'BlueGreenCement': 'Hard Court',
    'Clay': 'Clay',
    'Grass': 'Grass',
    'Indoor': 'Indoor'
  }
  return map[name] || name
})
</script>

<template>
  <div class="match-card" :class="{ 'is-live': server.is_started }">
    <!-- Header -->
    <div class="match-header">
      <span v-if="server.is_started" class="badge badge-live">
        <span class="live-dot"></span>
        LIVE
      </span>
      <span v-else class="badge badge-info">WAITING</span>
      <span class="badge" :class="surfaceClass">{{ surfaceDisplay }}</span>
    </div>

    <!-- Players -->
    <div class="match-players">
      <div class="player">
        <span class="player-name">{{ players.player1 }}</span>
        <span class="player-elo">ELO: {{ server.elo }}</span>
      </div>
      <span class="vs-separator">vs</span>
      <div class="player player-right">
        <span class="player-name">{{ players.player2 }}</span>
        <span class="player-elo">ELO: {{ server.other_elo }}</span>
      </div>
    </div>

    <!-- Score -->
    <div class="match-score" v-if="server.is_started && scoreDisplay.sets.length">
      <div class="score-sets">
        <span 
          v-for="(set, idx) in scoreDisplay.sets" 
          :key="idx"
          class="score-set"
        >
          {{ set }}
        </span>
      </div>
      <div class="score-current" v-if="scoreDisplay.currentGame">
        {{ scoreDisplay.currentGame }}
      </div>
    </div>

    <!-- Footer -->
    <div class="match-footer">
      <span class="match-mode">
        {{ server.game_info?.mode_display || 'Singles' }}
      </span>
      <span class="match-tag" v-if="server.tag_line">
        {{ server.tag_line }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.match-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  transition: all var(--transition-base);
}

.match-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.match-card.is-live {
  border-color: var(--color-error);
  box-shadow: 0 0 0 1px var(--color-error);
}

.match-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.live-dot {
  width: 6px;
  height: 6px;
  background: currentColor;
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.match-players {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.player {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.player-right {
  text-align: right;
}

.player-name {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}

.player-elo {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.vs-separator {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
}

.match-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
}

.score-sets {
  display: flex;
  gap: var(--space-2);
}

.score-set {
  font-family: var(--font-mono);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
}

.score-current {
  font-family: var(--font-mono);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-accent);
}

.match-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.match-mode {
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
}

.match-tag {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
