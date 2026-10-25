<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useScoresStore } from '@/stores/scores'

const store = useScoresStore()

const activeTimeRange = ref('this_month')

const timeRanges = [
  { id: 'this_month', label: 'This month' },
  { id: 'last_month', label: 'Last month' },
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
  return match ? match.label : 'This month'
}
</script>

<template>
  <section class="monthly-overview-section" aria-labelledby="activity-heading">
    <div class="overview-head">
      <h2 id="activity-heading">{{ getRangeTitle(activeTimeRange) }}</h2>
      <div class="seg" role="group" aria-label="Period">
        <button
          v-for="range in timeRanges"
          :key="range.id"
          type="button"
          :aria-pressed="activeTimeRange === range.id"
          @click="handleTabChange(range.id)"
        >
          {{ range.label }}
        </button>
      </div>
    </div>

    <div class="overview-grid">
      <div class="overview-card top-players-card">
        <div class="card-header">
          <h3>Most active players</h3>
          <span class="card-note">By matches played</span>
        </div>
        <table class="simple-table" v-if="store.topPlayers.length > 0">
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col" class="num-col">ELO</th>
              <th scope="col" class="num-col">Matches</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(player, index) in store.topPlayers" :key="player.name">
              <td class="player-col"><span class="rank-col">{{ index + 1 }}</span>{{ player.name }}</td>
              <td class="num-col">{{ player.latest_elo || '-' }}</td>
              <td class="num-col key-col">{{ player.matches }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="empty-note">No players found.</p>
      </div>

      <div class="overview-card monthly-averages-card">
        <div class="card-header">
          <h3>Daily averages by mod</h3>
          <span class="card-note" v-if="store.monthlyStats.days_recorded > 0">Based on {{ store.monthlyStats.days_recorded }} days</span>
        </div>
        <table class="simple-table" v-if="store.monthlyStats.days_recorded > 0">
          <thead>
            <tr>
              <th scope="col">Mod</th>
              <th scope="col" class="num-col">Per day</th>
              <th scope="col" class="num-col">1 set</th>
              <th scope="col" class="num-col">Bo3</th>
              <th scope="col" class="num-col">Bo5</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="player-col">XKT</td>
              <td class="num-col key-col">{{ store.monthlyStats.xkt.avg_total }}</td>
              <td class="num-col">{{ store.monthlyStats.xkt.avg_bo1 }}</td>
              <td class="num-col">{{ store.monthlyStats.xkt.avg_bo3 }}</td>
              <td class="num-col">{{ store.monthlyStats.xkt.avg_bo5 }}</td>
            </tr>
            <tr>
              <td class="player-col">WTSL</td>
              <td class="num-col key-col">{{ store.monthlyStats.wtsl.avg_total }}</td>
              <td class="num-col">{{ store.monthlyStats.wtsl.avg_bo1 }}</td>
              <td class="num-col">{{ store.monthlyStats.wtsl.avg_bo3 }}</td>
              <td class="num-col">{{ store.monthlyStats.wtsl.avg_bo5 }}</td>
            </tr>
            <tr>
              <td class="player-col">Vanilla</td>
              <td class="num-col key-col">{{ store.monthlyStats.vanilla.avg_total }}</td>
              <td class="num-col">{{ store.monthlyStats.vanilla.avg_bo1 }}</td>
              <td class="num-col">{{ store.monthlyStats.vanilla.avg_bo3 }}</td>
              <td class="num-col">{{ store.monthlyStats.vanilla.avg_bo5 }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="totals-row">
              <td class="player-col">All mods</td>
              <td class="num-col key-col">{{ store.monthlyStats.xkt.avg_total + store.monthlyStats.wtsl.avg_total + store.monthlyStats.vanilla.avg_total }}</td>
              <td class="num-col">{{ store.monthlyStats.xkt.avg_bo1 + store.monthlyStats.wtsl.avg_bo1 + store.monthlyStats.vanilla.avg_bo1 }}</td>
              <td class="num-col">{{ store.monthlyStats.xkt.avg_bo3 + store.monthlyStats.wtsl.avg_bo3 + store.monthlyStats.vanilla.avg_bo3 }}</td>
              <td class="num-col">{{ store.monthlyStats.xkt.avg_bo5 + store.monthlyStats.wtsl.avg_bo5 + store.monthlyStats.vanilla.avg_bo5 }}</td>
            </tr>
          </tfoot>
        </table>
        <p v-else class="empty-note">No daily data recorded yet.</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.monthly-overview-section {
  margin-top: var(--space-12);
}

.overview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.overview-head h2 {
  font-size: 1.25rem;
  letter-spacing: -0.01em;
}

.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  margin-top: var(--space-4);
  align-items: start;
}

.overview-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  padding: var(--space-2) var(--space-2) var(--space-3);
  min-width: 0;
  overflow-x: auto;
}

.card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3) var(--space-2);
  margin: 0;
}

.card-header h3 {
  font-family: var(--font-body);
  font-size: var(--font-size-base);
  font-weight: 600;
}

.card-note {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.simple-table th,
.simple-table td {
  border: none;
  border-bottom: 1px solid var(--color-border);
  padding: 0 var(--space-3);
  height: 44px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.simple-table thead th {
  border-bottom-color: var(--color-border-hover);
}

.simple-table tbody tr:last-child td {
  border-bottom: none;
}

.simple-table th {
  height: 36px;
  font-size: 0.8125rem;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-muted);
}

.simple-table .num-col {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.simple-table tbody tr {
  transition: background-color var(--transition-fast);
}

.simple-table tbody tr:hover {
  background: var(--color-bg-secondary);
}

.player-col {
  color: var(--color-text-primary);
  font-weight: 600;
}

.rank-col {
  display: inline-block;
  width: 28px;
  color: var(--color-text-muted);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.key-col {
  color: var(--color-text-primary);
  font-weight: 600;
}

.totals-row td {
  border-top: 1px solid var(--color-border-hover);
  border-bottom: none;
  color: var(--color-text-primary);
  font-weight: 600;
}

.empty-note {
  padding: var(--space-4) var(--space-3);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.seg {
  display: inline-flex;
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  padding: 3px;
}

.seg button {
  display: inline-flex;
  align-items: center;
  height: 34px;
  padding: 0 var(--space-4);
  border-radius: 6px;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.seg button:hover {
  color: var(--color-text-primary);
}

.seg button[aria-pressed="true"] {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

@media (max-width: 900px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
