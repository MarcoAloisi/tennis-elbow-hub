<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
} from 'chart.js'
import { useAnalysisStore } from '@/stores/analysis'
import { TrendingUp } from 'lucide-vue-next'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const store = useAnalysisStore()

// Stat options grouped by category
const statOptions = [
  { group: 'General', items: [
    { key: 'elo_cumulative', label: 'ELO Rating', unit: '', decimals: 0 },
    { key: 'elo_change', label: 'ELO Change Per Match', unit: '', decimals: 0 },
    { key: 'win_pct_rolling', label: 'Win % (Cumulative)', unit: '%', decimals: 1 },
  ]},
  { group: 'Serve', items: [
    { key: 'first_serve_pct', label: '1st Serve %', unit: '%', decimals: 1 },
    { key: 'aces', label: 'Aces', unit: '', decimals: 0 },
    { key: 'double_faults', label: 'Double Faults', unit: '', decimals: 0 },
    { key: 'avg_first_serve_kmh', label: 'Avg 1st Serve (km/h)', unit: ' km/h', decimals: 0 },
    { key: 'avg_second_serve_kmh', label: 'Avg 2nd Serve (km/h)', unit: ' km/h', decimals: 0 },
    { key: 'fastest_serve_kmh', label: 'Fastest Serve (km/h)', unit: ' km/h', decimals: 0 },
    { key: 'first_serve_won_pct', label: '1st Serve Won %', unit: '%', decimals: 1 },
    { key: 'second_serve_won_pct', label: '2nd Serve Won %', unit: '%', decimals: 1 },
  ]},
  { group: 'Rally', items: [
    { key: 'avg_rally_length', label: 'Avg Rally Length', unit: '', decimals: 1 },
    { key: 'short_rally_won_pct', label: 'Short Rally Won %', unit: '%', decimals: 1 },
    { key: 'medium_rally_won_pct', label: 'Medium Rally Won %', unit: '%', decimals: 1 },
    { key: 'long_rally_won_pct', label: 'Long Rally Won %', unit: '%', decimals: 1 },
  ]},
  { group: 'Points', items: [
    { key: 'winners', label: 'Winners', unit: '', decimals: 0 },
    { key: 'unforced_errors', label: 'Unforced Errors', unit: '', decimals: 0 },
    { key: 'forced_errors', label: 'Forced Errors', unit: '', decimals: 0 },
    { key: 'net_points_won_pct', label: 'Net Points Won %', unit: '%', decimals: 1 },
    { key: 'return_points_won_pct', label: 'Return Points Won %', unit: '%', decimals: 1 },
    { key: 'total_points_won_pct', label: 'Total Points Won %', unit: '%', decimals: 1 },
  ]},
  { group: 'Break Points', items: [
    { key: 'break_points_won_pct', label: 'Break Points Won %', unit: '%', decimals: 1 },
    { key: 'set_points_saved', label: 'Set Points Saved', unit: '', decimals: 0 },
    { key: 'match_points_saved', label: 'Match Points Saved', unit: '', decimals: 0 },
  ]}
]

const selectedStat = ref('elo_cumulative')

const currentStatMeta = computed(() => {
  for (const group of statOptions) {
    const found = group.items.find(i => i.key === selectedStat.value)
    if (found) return found
  }
  return { key: selectedStat.value, label: selectedStat.value, unit: '', decimals: 1 }
})

function getThemeColor(variable: string): string {
  const styles = getComputedStyle(document.documentElement)
  return styles.getPropertyValue(variable).trim()
}

const timeRanges = [
  { value: '1M', label: '1M' },
  { value: '3M', label: '3M' },
  { value: '6M', label: '6M' },
  { value: '1Y', label: '1Y' },
  { value: 'ALL', label: 'ALL' }
]
const selectedTimeRange = ref('ALL')

const filteredTimeSeries = computed(() => {
  const ts = store.matchTimeSeries
  if (!ts) return null
  
  const allValues = ts.stats[selectedStat.value] || []

  if (selectedTimeRange.value === 'ALL') {
    return {
      dates: ts.dates,
      opponents: ts.opponents,
      values: allValues
    }
  }

  // Find the most recent match date to use as 'now' instead of actual today
  // Since ts.rawDates is already sorted ascending by the store, the last valid date is simply at the end.
  let latestDate: Date | null = null
  for (let i = ts.rawDates.length - 1; i >= 0; i--) {
    if (ts.rawDates[i]) {
      latestDate = ts.rawDates[i]
      break
    }
  }

  if (!latestDate) return { dates: ts.dates, opponents: ts.opponents, values: allValues }
  
  const cutoffDate = new Date(latestDate.getTime())
  if (selectedTimeRange.value === '1M') cutoffDate.setMonth(latestDate.getMonth() - 1)
  else if (selectedTimeRange.value === '3M') cutoffDate.setMonth(latestDate.getMonth() - 3)
  else if (selectedTimeRange.value === '6M') cutoffDate.setMonth(latestDate.getMonth() - 6)
  else if (selectedTimeRange.value === '1Y') cutoffDate.setFullYear(latestDate.getFullYear() - 1)

  const filteredDates: string[] = []
  const filteredOpponents: string[] = []
  const filteredValues: number[] = []

  for (let i = 0; i < ts.rawDates.length; i++) {
    const d = ts.rawDates[i]
    if (d && d >= cutoffDate) {
      filteredDates.push(ts.dates[i])
      filteredOpponents.push(ts.opponents[i])
      filteredValues.push(allValues[i])
    }
  }

  // Always show at least some data if filtering removed everything
  if (filteredValues.length === 0) {
     return {
      dates: ts.dates,
      opponents: ts.opponents,
      values: allValues
    }
  }

  return {
    dates: filteredDates,
    opponents: filteredOpponents,
    values: filteredValues
  }
})

const chartData = computed(() => {
  const fts = filteredTimeSeries.value
  if (!fts || !fts.values.length) return null

  const primaryColor = getThemeColor('--color-brand-primary') || '#3BB143'

  return {
    labels: fts.dates,
    datasets: [{
      label: currentStatMeta.value.label,
      data: fts.values,
      borderColor: primaryColor,
      backgroundColor: `${primaryColor}22`,
      fill: true,
      tension: 0.3,
      pointRadius: fts.values.length > 50 ? 0 : 3,
      pointHoverRadius: 6,
      pointBackgroundColor: primaryColor,
      pointBorderColor: primaryColor,
      borderWidth: 2
    }]
  }
})

const chartOptions = computed(() => {
  const ts = store.matchTimeSeries
  const meta = currentStatMeta.value

  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(0,0,0,0.85)',
        titleColor: '#fff',
        bodyColor: '#ccc',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        displayColors: false,
        callbacks: {
          title: (items: any[]) => {
            if (!items.length || !filteredTimeSeries.value) return ''
            const idx = items[0].dataIndex
            const fts = filteredTimeSeries.value
            return `${fts.dates[idx]} — vs ${fts.opponents[idx]}`
          },
          label: (item: any) => {
            const val = item.parsed.y
            return `${meta.label}: ${val.toFixed(meta.decimals)}${meta.unit}`
          }
        }
      }
    },
    scales: {
      x: {
        grid: { color: 'rgba(255,255,255,0.05)' },
        ticks: {
          color: 'rgba(255,255,255,0.5)',
          maxRotation: 45,
          maxTicksLimit: 15,
          font: { size: 11 }
        }
      },
      y: {
        grid: { color: 'rgba(255,255,255,0.05)' },
        ticks: {
          color: 'rgba(255,255,255,0.5)',
          font: { size: 11 },
          callback: (value: number) => {
            if (meta.unit === '%') return `${value.toFixed(0)}%`
            return value.toFixed(0)
          }
        }
      }
    }
  }
})

// Summary stats for selected metric
const summaryStats = computed(() => {
  const fts = filteredTimeSeries.value
  if (!fts || !fts.values.length) return null

  const values = fts.values
  const avg = values.reduce((a, b) => a + b, 0) / values.length
  const min = Math.min(...values)
  const max = Math.max(...values)
  const latest = values[values.length - 1]
  const first = values[0]
  const trend = latest - first

  return { avg, min, max, latest, trend, count: values.length }
})
</script>

<template>
  <div class="perf-overview">
    <!-- Header -->
    <div class="perf-header">
      <div class="perf-title-row">
        <TrendingUp :size="20" class="title-icon" />
        <h3>Performance Trends</h3>
      </div>
      <div class="perf-controls">
        <div class="time-tabs">
          <button 
            v-for="tr in timeRanges" 
            :key="tr.value"
            class="time-tab"
            :class="{ active: selectedTimeRange === tr.value }"
            @click="selectedTimeRange = tr.value"
          >
            {{ tr.label }}
          </button>
        </div>
        <div class="stat-selector">
          <label for="stat-select" class="sr-only">Select statistic</label>
          <select id="stat-select" v-model="selectedStat" class="stat-select">
            <optgroup v-for="group in statOptions" :key="group.group" :label="group.group">
              <option v-for="item in group.items" :key="item.key" :value="item.key">
                {{ item.label }}
              </option>
            </optgroup>
          </select>
        </div>
      </div>
    </div>

    <!-- Summary Cards -->
    <div v-if="summaryStats" class="summary-cards">
      <div class="summary-card">
        <span class="summary-value">{{ summaryStats.latest.toFixed(currentStatMeta.decimals) }}{{ currentStatMeta.unit }}</span>
        <span class="summary-label">Latest</span>
      </div>
      <div class="summary-card">
        <span class="summary-value">{{ summaryStats.avg.toFixed(currentStatMeta.decimals) }}{{ currentStatMeta.unit }}</span>
        <span class="summary-label">Average</span>
      </div>
      <div class="summary-card">
        <span class="summary-value">{{ summaryStats.max.toFixed(currentStatMeta.decimals) }}{{ currentStatMeta.unit }}</span>
        <span class="summary-label">Best</span>
      </div>
      <div class="summary-card">
        <span class="summary-value" :class="summaryStats.trend >= 0 ? 'trend-up' : 'trend-down'">
          {{ summaryStats.trend >= 0 ? '+' : '' }}{{ summaryStats.trend.toFixed(currentStatMeta.decimals) }}
        </span>
        <span class="summary-label">Trend</span>
      </div>
    </div>

    <!-- Chart -->
    <div v-if="chartData" class="chart-wrapper">
      <Line :data="chartData" :options="chartOptions" />
    </div>
    <div v-else class="no-data">
      <p>No data available for the selected filters.</p>
    </div>
  </div>
</template>

<style scoped>
.perf-overview {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.perf-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.perf-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.title-icon {
  color: var(--color-accent);
}

.perf-title-row h3 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  border: 0;
}

.perf-controls {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.time-tabs {
  display: flex;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 2px;
}

.time-tab {
  background: transparent;
  border: none;
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-muted);
  border-radius: calc(var(--radius-md) - 2px);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.time-tab:hover {
  color: var(--color-text-primary);
}

.time-tab.active {
  background: var(--color-bg-secondary);
  color: var(--color-accent);
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.stat-select {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  min-width: 200px;
  cursor: pointer;
}

.stat-select:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.summary-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-3) var(--space-2);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.summary-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-accent);
  font-family: var(--font-mono);
}

.summary-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.trend-up {
  color: var(--color-success) !important;
}

.trend-down {
  color: var(--color-danger) !important;
}

.chart-wrapper {
  height: 350px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}

.no-data {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-text-muted);
}

@media (max-width: 640px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .perf-header {
    flex-direction: column;
    align-items: stretch;
  }

  .stat-select {
    width: 100%;
  }

  .chart-wrapper {
    height: 260px;
  }
}
</style>
