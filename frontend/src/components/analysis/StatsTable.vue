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
  },
  displayMode: {
    type: String,
    default: 'list' // 'list' or 'grid'
  }
})

// Define stat categories
const statCategories = {
  serve: [
    { key: 'first_serve_in', label: '1st Serve %', format: 'rate_pct', path: 'serve', total: 'first_serve_total' },
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
  
  // Helper to round visual numbers
  const r = (n) => Math.round(n)
  
  switch (stat.format) {
    case 'pct':
      return `${val.toFixed(1)}%`
    case 'speed':
      return `${val.toFixed(0)} km/h`
    case 'ratio':
      return total ? `${r(val)}/${r(total)}` : r(val).toString()
    case 'rate_pct':
      if (!total) {
          if (stat.total && !player[stat.path]?.[stat.total]) {
              return `${val.toFixed(1)}%`
          }
          return r(val).toString()
      }
      const totalVal = player[stat.path]?.[stat.total] || 0
      if (!totalVal) return `${val.toFixed(1)}%`
      
      const pct = totalVal > 0 ? Math.round((val / totalVal) * 100) : 0
      return `${r(val)}/${r(totalVal)} (${pct}%)`
    case 'dec':
      return val.toFixed(1)
    default:
      return val.toString()
  }
}

const isComparison = computed(() => {
    return props.player2 && Object.keys(props.player2).length > 0
})

function hasData(player, stat) {
    if (!player || !player[stat.path]) return false
    return true
}

function isWinner(stat) {
  // If not comparing, no winner/loser colors
  if (!isComparison.value) return { p1: false, p2: false }

  const v1 = getValue(props.player1, stat)
  const v2 = getValue(props.player2, stat)
  
  // Checking equality to avoid highlighting draws
  if (v1 === v2) return { p1: false, p2: false }

  // For stats where lower is better (errors), reverse comparison
  if (stat.lower) {
    return { p1: v1 < v2, p2: v2 < v1 }
  }
  return { p1: v1 > v2, p2: v2 > v1 }
}
</script>

<template>
  <div class="stats-table" :class="[{ 'single-col': !isComparison }, displayMode]">
    <div 
      v-for="stat in displayStats" 
      :key="stat.key"
      class="stats-row"
      :class="{ 'card-item': displayMode === 'grid' }"
    >
      <!-- Comparison View (Normal) -->
      <template v-if="displayMode === 'list'">
          <div 
            class="stats-value left"
            :class="{ winner: isComparison && isWinner(stat).p1 }"
          >
            {{ formatValue(player1, stat) }}
          </div>
          <div class="stats-label">
            {{ stat.label }}
          </div>
          <div 
            v-if="isComparison"
            class="stats-value right"
            :class="{ winner: isComparison && isWinner(stat).p2 }"
          >
            {{ formatValue(player2, stat) }}
          </div>
       </template>

       <!-- Grid View (Cards) -->
       <template v-else>
           <div class="card-label">{{ stat.label }}</div>
           <div class="card-values">
               <div class="p1-value" :class="{ winner: isComparison && isWinner(stat).p1 }">
                   <small v-if="isComparison">You</small>
                   <span>{{ formatValue(player1, stat) }}</span>
               </div>
               <div v-if="isComparison" class="vs-divider">vs</div>
               <div v-if="isComparison" class="p2-value" :class="{ winner: isComparison && isWinner(stat).p2 }">
                   <small>{{ player2.name || 'Opponent' }}</small>
                   <span>{{ formatValue(player2, stat) }}</span>
               </div>
           </div>
       </template>
    </div>
  </div>
</template>

<style scoped>
.stats-table {
  display: flex;
  flex-direction: column;
}

/* List Mode */
.stats-table.list .stats-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  transition: background-color var(--transition-fast);
}

.stats-table.list.single-col .stats-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-3) var(--space-6);
}

.stats-table.list.single-col .stats-label {
    text-align: left;
    min-width: 0;
    color: var(--color-text-primary);
    font-weight: var(--font-weight-medium);
}

.stats-table.list.single-col .stats-value.left {
    text-align: right;
    width: auto;
    margin: 0;
    font-weight: bold;
    color: var(--color-accent);
}

.stats-table.list .stats-row:hover {
  background: var(--color-bg-hover);
}

.stats-table.list .stats-row:last-child {
  border-bottom: none;
}

/* Grid Mode */
.stats-table.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: var(--space-4);
}

.stats-table.grid .stats-row.card-item {
    display: flex;
    flex-direction: column;
    padding: var(--space-4);
    background: var(--color-bg-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    gap: var(--space-3);
    align-items: center;
    text-align: center;
    box-shadow: var(--shadow-sm);
    transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.stats-table.grid .stats-row.card-item:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}

.card-label {
    font-size: var(--font-size-xs);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    font-weight: var(--font-weight-bold);
}

.card-values {
    display: flex;
    align-items: baseline; /* Align by baseline for better text flow */
    justify-content: center;
    gap: var(--space-4);
    width: 100%;
}

.p1-value, .p2-value {
    display: flex;
    flex-direction: column;
    align-items: center;
    font-family: var(--font-mono);
    font-weight: bold;
    font-size: var(--font-size-md); /* Reduced from lg to prevent overflow */
}

.p1-value small, .p2-value small {
    font-size: 0.7rem;
    color: var(--color-text-muted);
    font-weight: normal;
    font-family: var(--font-body);
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 80px; /* Constrain name width */
}

.vs-divider {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    align-self: center;
}

/* Common Value Styles */
.stats-value {
  font-weight: var(--font-weight-medium);
  font-family: var(--font-data);
  color: var(--color-text-primary);
}

.stats-value.left {
  text-align: right;
}

.stats-value.right {
  text-align: left;
}

.stats-value.winner, .p1-value.winner, .p2-value.winner span {
  color: var(--color-brand-primary);
  font-weight: var(--font-weight-bold);
}

.stats-label {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  min-width: 160px;
}
</style>
