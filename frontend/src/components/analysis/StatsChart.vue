<script setup>
import { computed, ref, onMounted } from 'vue'
import { Radar, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement
} from 'chart.js'

// Register Chart.js components
ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement
)

const props = defineProps({
  player1: {
    type: Object,
    required: true
  },
  player2: {
    type: Object,
    required: true
  },
  chartType: {
    type: String,
    default: 'radar',
    validator: (v) => ['radar', 'bar'].includes(v)
  }
})

const selectedChart = ref(props.chartType)

// Normalize values to 0-100 scale for radar chart
function normalize(value, max) {
  return Math.min(100, (value / max) * 100)
}

// Radar chart data
const radarData = computed(() => {
  const p1 = props.player1
  const p2 = props.player2

  // Calculate composite scores
  const labels = ['Serve Power', 'Accuracy', 'Net Game', 'Rally', 'Break Points', 'Consistency']
  
  // Player 1 values
  const p1Values = [
    normalize(p1.serve?.avg_first_serve_kmh || 0, 250),
    p1.serve?.first_serve_pct || 0,
    normalize(p1.points?.net_points_won || 0, 10),
    normalize(p1.rally?.long_rallies_won || 0, 15),
    normalize(p1.break_points?.break_points_won || 0, 5),
    100 - normalize(p1.points?.unforced_errors || 0, 30)
  ]

  // Player 2 values
  const p2Values = [
    normalize(p2.serve?.avg_first_serve_kmh || 0, 250),
    p2.serve?.first_serve_pct || 0,
    normalize(p2.points?.net_points_won || 0, 10),
    normalize(p2.rally?.long_rallies_won || 0, 15),
    normalize(p2.break_points?.break_points_won || 0, 5),
    100 - normalize(p2.points?.unforced_errors || 0, 30)
  ]

  return {
    labels,
    datasets: [
      {
        label: p1.name || 'Player 1',
        data: p1Values,
        backgroundColor: 'rgba(79, 70, 229, 0.2)',
        borderColor: 'rgb(79, 70, 229)',
        borderWidth: 2,
        pointBackgroundColor: 'rgb(79, 70, 229)'
      },
      {
        label: p2.name || 'Player 2',
        data: p2Values,
        backgroundColor: 'rgba(239, 68, 68, 0.2)',
        borderColor: 'rgb(239, 68, 68)',
        borderWidth: 2,
        pointBackgroundColor: 'rgb(239, 68, 68)'
      }
    ]
  }
})

// Bar chart data comparing key stats
const barData = computed(() => {
  const p1 = props.player1
  const p2 = props.player2

  return {
    labels: ['Winners', 'Aces', 'Break Pts', 'Net Pts'],
    datasets: [
      {
        label: p1.name || 'Player 1',
        data: [
          p1.points?.winners || 0,
          p1.serve?.aces || 0,
          p1.break_points?.break_points_won || 0,
          p1.points?.net_points_won || 0
        ],
        backgroundColor: 'rgba(79, 70, 229, 0.8)',
        borderRadius: 4
      },
      {
        label: p2.name || 'Player 2',
        data: [
          p2.points?.winners || 0,
          p2.serve?.aces || 0,
          p2.break_points?.break_points_won || 0,
          p2.points?.net_points_won || 0
        ],
        backgroundColor: 'rgba(239, 68, 68, 0.8)',
        borderRadius: 4
      }
    ]
  }
})

const radarOptions = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: {
      position: 'bottom'
    }
  },
  scales: {
    r: {
      min: 0,
      max: 100,
      ticks: {
        stepSize: 20
      }
    }
  }
}

const barOptions = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: {
      position: 'bottom'
    }
  },
  scales: {
    y: {
      beginAtZero: true
    }
  }
}
</script>

<template>
  <div class="stats-chart">
    <!-- Chart type selector -->
    <div class="chart-selector">
      <button 
        class="chart-btn"
        :class="{ active: selectedChart === 'radar' }"
        @click="selectedChart = 'radar'"
      >
        📊 Radar
      </button>
      <button 
        class="chart-btn"
        :class="{ active: selectedChart === 'bar' }"
        @click="selectedChart = 'bar'"
      >
        📈 Bar
      </button>
    </div>

    <!-- Charts -->
    <div class="chart-container">
      <Radar 
        v-if="selectedChart === 'radar'"
        :data="radarData" 
        :options="radarOptions"
      />
      <Bar 
        v-else
        :data="barData" 
        :options="barOptions"
      />
    </div>
  </div>
</template>

<style scoped>
.stats-chart {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.chart-selector {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.chart-btn {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  transition: all var(--transition-fast);
}

.chart-btn:hover {
  background: var(--color-bg-hover);
}

.chart-btn.active {
  background: var(--color-accent);
  color: white;
  border-color: var(--color-accent);
}

.chart-container {
  max-width: 500px;
  margin: 0 auto;
}
</style>
