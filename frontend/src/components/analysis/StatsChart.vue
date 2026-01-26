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

// Helper to get CSS variable value
function getThemeColor(variable) {
  const styles = getComputedStyle(document.documentElement)
  return styles.getPropertyValue(variable).trim()
}


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
    p1.points?.net_points_won || 0, // Using pct from analysis
    p1.rally?.short_rallies_won || 0, // Actually rally won pct is pre-calculated in analysis mapping?
    // Wait, in StatsTable I see 'net_points_won' mapped to 'net_points_won_pct' in matchAnalysis?
    // Let's check 'mapStatsToStructure' in MatchAnalysisView:
    // net_points_won: s.net_points_won_pct.
    // So here p1.points.net_points_won IS the percentage!
    // So normalize(..., 10) was wrong if it's already %.
    // If it's percentage (0-100), we don't need normalize.
    
    // Break Points:
    p1.break_points?.break_points_won || 0, // This is mapped to break_points_won_pct (0-100)
    
    // Consistency: Errors.
    // Errors are raw counts.
    100 - normalize(p1.points?.unforced_errors || 0, 30)
  ]
  
  // Rally: short_rallies_won in View mapping is 'short_rally_won_pct'.
  // But radar label is 'Rally'. Usually implies winning long rallies?
  // Previous code: p1.rally?.long_rallies_won (PCT).
  // Let's use long rally win %.
  
  // Updated P1 Values
  // 1. Power (kmh/250)
  // 2. Accuracy (1st pct)
  // 3. Net Game (Net Won Pct)
  // 4. Rally (Long Rally Won Pct)
  // 5. Break Points (BP Won Pct)
  // 6. Consistency (100 - normalized Errors)

  const p1Vals = [
      normalize(p1.serve?.avg_first_serve_kmh || 0, 250),
      p1.serve?.first_serve_pct || 0,
      p1.points?.net_points_won || 0, // Already %
      p1.rally?.long_rallies_won || 0, // Already % (mapped from long_rally_won_pct)
      p1.break_points?.break_points_won || 0, // Already %
      100 - normalize(p1.points?.unforced_errors || 0, 30) // Errors are Count
  ]

  // Player 2 values
  const p2Vals = [
      normalize(p2.serve?.avg_first_serve_kmh || 0, 250),
      p2.serve?.first_serve_pct || 0,
      p2.points?.net_points_won || 0,
      p2.rally?.long_rallies_won || 0,
      p2.break_points?.break_points_won || 0,
      100 - normalize(p2.points?.unforced_errors || 0, 30)
  ]
  
  const p1Values = p1Vals
  const p2Values = p2Vals

  const primaryColor = getThemeColor('--color-brand-primary') || '#3BB143'
  const secondaryColor = getThemeColor('--color-text-secondary') || '#64748b'

  // Convert hex to rgba for background (simple implementation)
  const hexToRgba = (hex, alpha) => {
    let r = 0, g = 0, b = 0
    if (hex.length === 4) {
      r = parseInt(hex[1] + hex[1], 16)
      g = parseInt(hex[2] + hex[2], 16)
      b = parseInt(hex[3] + hex[3], 16)
    } else if (hex.length === 7) {
      r = parseInt(hex[1] + hex[2], 16)
      g = parseInt(hex[3] + hex[4], 16)
      b = parseInt(hex[5] + hex[6], 16)
    }
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
  }

  return {
    labels,
    datasets: [
      {
        label: p1.name || 'Player 1',
        data: p1Values,
        backgroundColor: hexToRgba(primaryColor, 0.2),
        borderColor: primaryColor,
        borderWidth: 2,
        pointBackgroundColor: primaryColor
      },
      {
        label: p2.name || 'Player 2',
        data: p2Values,
        backgroundColor: hexToRgba(secondaryColor, 0.2),
        borderColor: secondaryColor,
        borderDash: [5, 5], // Dotted line for comparison
        borderWidth: 2,
        pointBackgroundColor: secondaryColor
      }
    ]
  }
})

// Bar chart data comparing key stats
const barData = computed(() => {
  const p1 = props.player1
  const p2 = props.player2

  const primaryColor = getThemeColor('--color-brand-primary') || '#3BB143'
  const secondaryColor = getThemeColor('--color-text-secondary') || '#64748b'

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
        backgroundColor: primaryColor,
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
        backgroundColor: secondaryColor,
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
