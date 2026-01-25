<script setup>
import { computed } from 'vue'

const props = defineProps({
  player1: {
    type: Object,
    required: true
  },
  player2: {
    type: Object,
    required: true
  },
  category: {
    type: String,
    default: 'all'
  }
})

// Define stat categories
const statCategories = {
  serve: [
    { key: 'first_serve_pct', label: '1st Serve %', format: 'rate_pct', path: 'serve', total: 'first_serve_total', value: 'first_serve_in' },
    { key: 'aces', label: 'Aces', format: 'num', path: 'serve' },
    { key: 'double_faults', label: 'Double Faults', format: 'num', path: 'serve', lower: true },
    { key: 'avg_first_serve_kmh', label: 'Avg 1st Serve (km/h)', format: 'speed', path: 'serve' },
    { key: 'avg_second_serve_kmh', label: 'Avg 2nd Serve (km/h)', format: 'speed', path: 'serve' },
    { key: 'fastest_serve_kmh', label: 'Fastest Serve (km/h)', format: 'speed', path: 'serve' }
  ],
  rally: [
    { key: 'short_rallies_won', label: 'Short Rallies (<5)', format: 'rate_pct', path: 'rally', total: 'short_rallies_total' },
    { key: 'normal_rallies_won', label: 'Medium Rallies (5-8)', format: 'rate_pct', path: 'rally', total: 'normal_rallies_total' },
    { key: 'long_rallies_won', label: 'Long Rallies (>8)', format: 'rate_pct', path: 'rally', total: 'long_rallies_total' },
    { key: 'avg_rally_length', label: 'Avg Rally Length', format: 'dec', path: 'rally' }
  ],
  points: [
    { key: 'winners', label: 'Winners', format: 'num', path: 'points' },
    { key: 'forced_errors', label: 'Forced Errors', format: 'num', path: 'points', lower: true },
    { key: 'unforced_errors', label: 'Unforced Errors', format: 'num', path: 'points', lower: true },
    { key: 'points_on_first_serve_won', label: '1st Serve Won %', format: 'rate_pct', path: 'points', total: 'points_on_first_serve_total' },
    { key: 'points_on_second_serve_won', label: '2nd Serve Won %', format: 'rate_pct', path: 'points', total: 'points_on_second_serve_total' },
    { key: 'return_points_won', label: 'Return Points Won', format: 'rate_pct', path: 'points', total: 'return_points_total' },
    { key: 'return_winners', label: 'Return Winners', format: 'num', path: 'points' },
    { key: 'net_points_won', label: 'Net Points Won', format: 'rate_pct', path: 'points', total: 'net_points_total' },
    { key: 'total_points_won', label: 'Total Points Won', format: 'num', path: 'points' }
  ],
  break_points: [
    { key: 'break_points_won', label: 'Break Points Won', format: 'rate_pct', path: 'break_points', total: 'break_points_total' },
    { key: 'break_games_won', label: 'Breaks / Games', format: 'rate_pct', path: 'break_points', total: 'break_games_total' }, 
    { key: 'set_points_saved', label: 'Set Points Saved', format: 'num', path: 'break_points' },
    { key: 'match_points_saved', label: 'Match Points Saved', format: 'num', path: 'break_points' }
  ]
}

const displayStats = computed(() => {
  if (props.category === 'all') {
    return Object.values(statCategories).flat()
  }
  return statCategories[props.category] || []
})

function getValue(player, stat) {
  // Special case for nested keys in same path (like avg serve speed)
  const key = stat.key || stat.keyAlias
  const section = player[stat.path]
  if (!section) return 0
  return section[key] ?? 0
}

function getTotal(player, stat) {
  if (!stat.total) return null
  const section = player[stat.path]
  return section?.[stat.total] ?? 0
}

function formatValue(player, stat) {
  const val = getValue(player, stat)
  const total = getTotal(player, stat)
  
  switch (stat.format) {
    case 'pct':
      return `${val.toFixed(1)}%`
    case 'speed':
      return `${val.toFixed(0)} km/h`
    case 'ratio':
      return total ? `${val}/${total}` : val.toString()
    case 'rate_pct':
      if (!total) return val.toString()
      const pct = total > 0 ? Math.round((val / total) * 100) : 0
      return `${val} / ${total} = ${pct}%`
    case 'dec':
      return val.toFixed(1)
    default:
      return val.toString()
  }
}

function isWinner(stat) {
  const v1 = getValue(props.player1, stat)
  const v2 = getValue(props.player2, stat)
  
  // For stats where lower is better (errors), reverse comparison
  if (stat.lower) {
    return { p1: v1 < v2, p2: v2 < v1 }
  }
  return { p1: v1 > v2, p2: v2 > v1 }
}
</script>

<template>
  <div class="stats-table">
    <div 
      v-for="stat in displayStats" 
      :key="stat.key"
      class="stats-row"
    >
      <div 
        class="stats-value left"
        :class="{ winner: isWinner(stat).p1 }"
      >
        {{ formatValue(player1, stat) }}
      </div>
      <div class="stats-label">
        {{ stat.label }}
      </div>
      <div 
        class="stats-value right"
        :class="{ winner: isWinner(stat).p2 }"
      >
        {{ formatValue(player2, stat) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-table {
  display: flex;
  flex-direction: column;
}

.stats-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  transition: background-color var(--transition-fast);
}

.stats-row:hover {
  background: var(--color-bg-hover);
}

.stats-row:last-child {
  border-bottom: none;
}

.stats-value {
  font-weight: var(--font-weight-medium);
  font-family: var(--font-mono);
  color: var(--color-text-primary);
}

.stats-value.left {
  text-align: right;
}

.stats-value.right {
  text-align: left;
}

.stats-value.winner {
  color: var(--color-success);
  font-weight: var(--font-weight-bold);
}

.stats-label {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  min-width: 160px;
}
</style>
