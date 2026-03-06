<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useScoresStore } from '@/stores/scores'

const store = useScoresStore()

const activeTimeRange = ref('this_month')

const timeRanges = [
  { id: 'this_month', label: 'This Month' },
  { id: 'last_month', label: 'Last Month' },
  { id: 'year', label: 'Yearly' }
]

function handleTabChange(rangeId: string) {
  activeTimeRange.value = rangeId
  store.fetchTopPlayers(rangeId)
  store.fetchMonthlyStats(rangeId)
}

// Map the range ID to the title text
function getRangeTitle(rangeId: string) {
  const match = timeRanges.find(tr => tr.id === rangeId)
  return match ? match.label : 'This Month'
}
</script>

<template>
  <div class="monthly-overview-section">
    <!-- Time Range Tabs -->
    <div class="time-range-tabs">
      <button 
        v-for="range in timeRanges" 
        :key="range.id"
        class="time-tab-btn"
        :class="{ active: activeTimeRange === range.id }"
        @click="handleTabChange(range.id)"
      >
        {{ range.label }}
      </button>
    </div>

    <!-- Top 5 Players Card -->
    <div class="overview-card top-players-card">
      <div class="card-header">
        <h3>Most active players ({{ getRangeTitle(activeTimeRange) }})</h3>
      </div>
      <div class="card-content">
        <table class="simple-table" v-if="store.topPlayers.length > 0">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Player</th>
              <th class="text-right">ELO</th>
              <th class="text-right">Matches</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(player, index) in store.topPlayers" :key="player.name">
              <td class="rank-col">#{{ index + 1 }}</td>
              <td class="player-col">{{ player.name }}</td>
              <td class="text-right font-bold elo-highlight">{{ player.latest_elo || '-' }}</td>
              <td class="matches-col text-right">{{ player.matches }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-muted">No players found.</p>
      </div>
    </div>

    <!-- Monthly Averages Card -->
    <div class="overview-card monthly-averages-card">
      <div class="card-header">
        <h3>Daily Averages ({{ getRangeTitle(activeTimeRange) }})</h3>
        <span class="days-recorded">Based on {{ store.monthlyStats.days_recorded }} days</span>
      </div>
      <div class="card-content">
        <table class="simple-table averages-table" v-if="store.monthlyStats.days_recorded > 0">
          <thead>
            <tr>
              <th>Mod</th>
              <th class="text-center">Total/Day</th>
              <th class="text-center">BO1</th>
              <th class="text-center">BO3</th>
              <th class="text-center">BO5</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="mod-name">XKT</td>
              <td class="text-center font-bold">{{ store.monthlyStats.xkt.avg_total }}</td>
              <td class="text-center">{{ store.monthlyStats.xkt.avg_bo1 }}</td>
              <td class="text-center">{{ store.monthlyStats.xkt.avg_bo3 }}</td>
              <td class="text-center">{{ store.monthlyStats.xkt.avg_bo5 }}</td>
            </tr>
            <tr>
              <td class="mod-name">WTSL</td>
              <td class="text-center font-bold">{{ store.monthlyStats.wtsl.avg_total }}</td>
              <td class="text-center">{{ store.monthlyStats.wtsl.avg_bo1 }}</td>
              <td class="text-center">{{ store.monthlyStats.wtsl.avg_bo3 }}</td>
              <td class="text-center">{{ store.monthlyStats.wtsl.avg_bo5 }}</td>
            </tr>
            <tr>
              <td class="mod-name">Vanilla</td>
              <td class="text-center font-bold">{{ store.monthlyStats.vanilla.avg_total }}</td>
              <td class="text-center">{{ store.monthlyStats.vanilla.avg_bo1 }}</td>
              <td class="text-center">{{ store.monthlyStats.vanilla.avg_bo3 }}</td>
              <td class="text-center">{{ store.monthlyStats.vanilla.avg_bo5 }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="totals-row">
              <td class="mod-name totals-label">Total Avg</td>
              <td class="text-center font-bold totals-value">{{ store.monthlyStats.xkt.avg_total + store.monthlyStats.wtsl.avg_total + store.monthlyStats.vanilla.avg_total }}</td>
              <td class="text-center font-bold">{{ store.monthlyStats.xkt.avg_bo1 + store.monthlyStats.wtsl.avg_bo1 + store.monthlyStats.vanilla.avg_bo1 }}</td>
              <td class="text-center font-bold">{{ store.monthlyStats.xkt.avg_bo3 + store.monthlyStats.wtsl.avg_bo3 + store.monthlyStats.vanilla.avg_bo3 }}</td>
              <td class="text-center font-bold">{{ store.monthlyStats.xkt.avg_bo5 + store.monthlyStats.wtsl.avg_bo5 + store.monthlyStats.vanilla.avg_bo5 }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* Time Range Tabs */
.time-range-tabs {
  grid-column: 1 / -1;
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-3);
}

.time-tab-btn {
  padding: var(--space-2) var(--space-4);
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.time-tab-btn:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
}

.time-tab-btn.active {
  background: var(--color-accent);
  color: var(--color-text-inverse);
  border-color: var(--color-accent);
}

/* Monthly Overview Section */
.monthly-overview-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
  margin-bottom: var(--space-8);
}

.overview-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.overview-card .card-header {
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.overview-card .card-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.days-recorded {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.overview-card .card-content {
  padding: 0;
  flex: 1;
}

/* Simple Table Styling */
.simple-table {
  width: 100%;
  border-collapse: collapse;
}

.simple-table th, 
.simple-table td {
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  font-size: 0.9rem;
}

.simple-table th {
  text-align: left;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
}

.simple-table tbody tr:last-child td {
  border-bottom: none;
}

.simple-table tbody tr:hover {
  background: var(--color-bg-hover);
}

.totals-row td {
  border-top: 2px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.text-right, .simple-table th.text-right { text-align: right; }
.text-center, .simple-table th.text-center { text-align: center; }
.text-muted { color: var(--color-text-muted); padding: var(--space-4) var(--space-5); }
.font-bold { font-weight: 700; color: var(--color-brand-live); }

.rank-col { width: 60px; color: var(--color-text-muted); font-weight: 600; }
.player-col { font-weight: 600; color: var(--color-text-primary); }
.matches-col { font-weight: 700; color: var(--color-brand-primary); }
.mod-name { font-weight: 600; }
.elo-highlight { color: var(--color-brand-accent); }
.totals-label { color: var(--color-text-secondary); text-transform: uppercase; }
.totals-value { color: var(--color-brand-primary); }

@media (max-width: 768px) {
  .monthly-overview-section {
    grid-template-columns: 1fr;
  }
}
</style>
