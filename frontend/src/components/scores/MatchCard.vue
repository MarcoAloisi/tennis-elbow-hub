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
  
  // Try " vs " separator
  if (name.includes(' vs ')) {
    const parts = name.split(' vs ')
    return { player1: parts[0].trim(), player2: parts[1].trim() }
  }
  
  // Try " - " separator
  if (name.includes(' - ')) {
    const parts = name.split(' - ')
    return { player1: parts[0].trim(), player2: parts[1].trim() }
  }
  
  // Single player or unknown format
  return { player1: name, player2: null }
})

// Parse score for display and determine who is serving
const scoreDisplay = computed(() => {
  const score = props.server.score || ''
  // Format: "6/3 4/6 1/1 -- 00:40•" or "6/3 4/6 1/1 -- •00:40"
  const parts = score.split(' -- ')
  const sets = parts[0] ? parts[0].trim().split(' ') : []
  let currentGame = parts[1] ? parts[1].trim() : ''
  
  // Detect which player is serving based on • position
  // • at the start means player 1 is serving, at the end means player 2
  let servingPlayer = 0 // 0 = unknown, 1 = player1, 2 = player2
  if (currentGame.startsWith('•')) {
    servingPlayer = 1
    currentGame = currentGame.substring(1) // Remove the •
  } else if (currentGame.endsWith('•')) {
    servingPlayer = 2
    currentGame = currentGame.substring(0, currentGame.length - 1) // Remove the •
  }
  
  return { sets, currentGame, servingPlayer }
})

// Surface badge class - determine from surface_display (computed by backend)
const surfaceClass = computed(() => {
  const surface = (props.server.surface_display || props.server.surface_name || '').toLowerCase()
  if (surface.includes('clay')) return 'badge-surface-clay'
  if (surface.includes('grass')) return 'badge-surface-grass'
  if (surface.includes('indoor')) return 'badge-surface-indoor'
  return 'badge-surface-hard'
})

// Format surface name - prefer backend-computed value
const surfaceDisplay = computed(() => {
  // Use backend-computed surface_display if available
  if (props.server.surface_display) {
    return props.server.surface_display
  }
  
  const name = props.server.surface_name || ''
  const map = {
    'BlueGreenCement': 'Hard Court',
    'Clay': 'Clay',
    'Grass': 'Grass',
    'Indoor': 'Indoor'
  }
  return map[name] || name
})

// Tournament name - cleaned up (without numeric prefix)
const tournamentDisplay = computed(() => {
  // Use backend-computed tournament_display if available
  if (props.server.tournament_display) {
    return props.server.tournament_display
  }
  
  const name = props.server.surface_name || ''
  // Remove numeric prefix like "0010 " or "00031 "
  return name.replace(/^\d+\s+/, '')
})

// Number of sets display
const setsDisplay = computed(() => {
  return props.server.game_info?.sets_display || ''
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
      <span v-if="tournamentDisplay" class="badge badge-tournament">{{ tournamentDisplay }}</span>
      <span v-else class="badge" :class="surfaceClass">{{ surfaceDisplay }}</span>
    </div>

    <!-- Players -->
    <div class="match-players" :class="{ 'single-player': !players.player2 }">
      <div class="player">
        <span class="player-name">
          <span v-if="scoreDisplay.servingPlayer === 1" class="serving-ball">🎾</span>
          {{ players.player1 }}
        </span>
        <span class="player-elo">ELO: {{ server.elo }}</span>
        <span class="player-games">{{ server.nb_game }} games</span>
      </div>
      <span class="vs-separator" v-if="players.player2">vs</span>
      <div class="player player-right" v-if="players.player2">
        <span class="player-name">
          {{ players.player2 }}
          <span v-if="scoreDisplay.servingPlayer === 2" class="serving-ball">🎾</span>
        </span>
        <span class="player-elo">ELO: {{ server.other_elo }}</span>
        <span class="player-games">{{ server.other_elo > 0 ? '' : '' }}</span>
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
      <span v-if="setsDisplay" class="match-sets">
        {{ setsDisplay }}
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

.match-players.single-player {
  display: flex;
  justify-content: center;
  text-align: center;
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

.player-games {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  opacity: 0.8;
}

.serving-ball {
  display: inline-block;
  animation: bounce 0.6s infinite ease-in-out;
  margin-right: 4px;
  font-size: 0.9em;
}

.player-right .serving-ball {
  margin-right: 0;
  margin-left: 4px;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-3px);
  }
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
  gap: var(--space-2);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.match-mode {
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
}

.match-sets {
  padding: var(--space-1) var(--space-2);
  background: var(--color-accent-light, rgba(99, 102, 241, 0.1));
  color: var(--color-accent);
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
}

.match-tag {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge-tournament {
  background: var(--color-bg-tertiary, #f3f4f6);
  color: var(--color-text-secondary, #6b7280);
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
