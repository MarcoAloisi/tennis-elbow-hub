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
  matchInfo: {
    type: Object,
    default: () => ({})
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
  return Math.min(100, Math.max(0, (value / max) * 100))
}

// Radar chart data
const radarData = computed(() => {
  const p1 = props.player1
  const p2 = props.player2

  // --- VERTEX 1: SERVE POWER ---
  // Formula: ((Avg 1st / 210) * 70) + ((Peak / 230) * 30)
  const calcPower = (p) => {
    const avg = p.serve?.avg_first_serve_kmh || 0
    const fast = p.serve?.fastest_serve_kmh || 0
    // Updated avg baseline to 210 as per v1.0 spec
    const score = ((avg / 210) * 70) + ((fast / 230) * 30)
    return Math.min(100, Math.max(0, score))
  }

  // --- VERTEX 2: SERVE ACCURACY ---
  // Formula: ((1st% * 0.6) + (2nd% * 0.4)) - ((DF / TotalServicePoints) * 100)
  const calcServeAccuracy = (p) => {
    const firstPct = p.serve?.first_serve_pct || 0
    
    const secWon = p.points?.points_on_second_serve_won || 0
    const secTotal = p.points?.points_on_second_serve_total || 0
    const secPct = secTotal > 0 ? (secWon / secTotal) * 100 : 0
    
    // Calculate total service points for normalization
    const pointsFirst = p.points?.points_on_first_serve_total || 0
    const pointsSecond = p.points?.points_on_second_serve_total || 0
    const totalServicePoints = pointsFirst + pointsSecond
    
    const df = p.serve?.double_faults || 0
    
    let penalty = 0
    if (totalServicePoints > 0) {
      penalty = (df / totalServicePoints) * 100
    }
    
    const score = ((firstPct * 0.6) + (secPct * 0.4)) - penalty
    return Math.min(100, Math.max(0, score))
  }

  // --- VERTEX 3: CONSISTENCY ---
  // Formula: (Winners / (Winners + UE + (0.25 * FE))) * 100
  const calcConsistency = (p) => {
    const w = p.points?.winners || 0
    const ue = p.points?.unforced_errors || 0
    const fe = p.points?.forced_errors || 0
    
    const denominator = w + ue + (0.25 * fe)
    if (denominator === 0) return 0
    return (w / denominator) * 100
  }

  // --- VERTEX 4: NET GAME ---
  // Formula: NetWon% * Volume_Coefficient
  const calcNetGame = (p) => {
    const won = p.points?.net_points_won || 0
    const total = p.points?.net_points_total || 0 
    if (total === 0) return 0
    
    const winPct = (won / total) * 100
    
    // Discrete Volume Coefficients
    let multiplier = 1.0
    if (total < 5) {
      multiplier = 0.5
    } else if (total > 20) {
      multiplier = 1.1
    } else {
      multiplier = 1.0 // 5-20
    }
    
    return winPct * multiplier
  }

  // --- VERTEX 5: RALLY ---
  // Formula: (Short% * 0.2) + (Med% * 0.4) + (Long% * 0.4)
  const calcRally = (p) => {
    const getWinPct = (won, total) => total > 0 ? (won / total) * 100 : 0
    
    const shortPct = getWinPct(p.rally?.short_rallies_won || 0, p.rally?.short_rallies_total || 0)
    const medPct = getWinPct(p.rally?.normal_rallies_won || 0, p.rally?.normal_rallies_total || 0)
    const longPct = getWinPct(p.rally?.long_rallies_won || 0, p.rally?.long_rallies_total || 0)
    
    return (shortPct * 0.2) + (medPct * 0.4) + (longPct * 0.4)
  }

  // --- VERTEX 6: PRESSURE POINTS ---
  // Formula: (BP% * 0.5) + (Ret% * 0.3) + Bonus
  const calcPressurePoints = (p) => {
    const bpWon = p.break_points?.break_points_won || 0
    const bpTotal = p.break_points?.break_points_total || 0
    const bpPct = bpTotal > 0 ? (bpWon / bpTotal) * 100 : 0
    
    const retWon = p.points?.return_points_won || 0
    const retTotal = p.points?.return_points_total || 0
    const retPct = retTotal > 0 ? (retWon / retTotal) * 100 : 0
    
    // Bonus Logic: +5 if ANY set or match points saved
    const setSaved = p.break_points?.set_points_saved || 0
    const matchSaved = p.break_points?.match_points_saved || 0
    const bonus = (setSaved > 0 || matchSaved > 0) ? 5 : 0
    
    const score = (bpPct * 0.5) + (retPct * 0.3) + bonus
    
    return Math.min(100, Math.max(0, score))
  }

  const labels = ['Serve Power', 'Serve Accuracy', 'Consistency', 'Net Game', 'Rally Resilience', 'Pressure Points']
  
  const p1Values = [
    calcPower(p1),
    calcServeAccuracy(p1),
    calcConsistency(p1),
    calcNetGame(p1),
    calcRally(p1),
    calcPressurePoints(p1)
  ]

  const p2Values = [
    calcPower(p2),
    calcServeAccuracy(p2),
    calcConsistency(p2),
    calcNetGame(p2),
    calcRally(p2),
    calcPressurePoints(p2)
  ]

  const primaryColor = getThemeColor('--color-brand-primary') || '#3BB143'
  const secondaryColor = getThemeColor('--color-text-secondary') || '#64748b'

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
        borderDash: [5, 5],
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
    <div class="header-row">
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
    </div>

    <div class="content-grid">
      <!-- Legend / Explainer (Only for Radar) -->
      <div v-if="selectedChart === 'radar'" class="chart-legend">
        <h3>How it Works</h3>
        <ul class="legend-list">
          <li>
            <span class="label">Serve Power</span>
            <span class="desc">Weighted Speed Index</span>
            <span class="formula">((Avg/210)*70) + ((Pk/230)*30)</span>
          </li>
          <li>
            <span class="label">Serve Accuracy</span>
            <span class="desc">Reliability & Discipline</span>
            <span class="formula">((1st*0.6)+(2nd*0.4)) - (DF/Pts*100)</span>
          </li>
          <li>
            <span class="label">Consistency</span>
            <span class="desc">Point Ending Efficiency</span>
            <span class="formula">Win / (Win + UE + 0.25*FE)</span>
          </li>
          <li>
            <span class="label">Net Game</span>
            <span class="desc">Success Rate with Volume Penalty</span>
            <span class="formula">Net% * Vol_Coef (0.5, 1.0, 1.1)</span>
          </li>
          <li>
            <span class="label">Rally Resilience</span>
            <span class="desc">All-Range Domination</span>
            <span class="formula">(Sht*0.2) + (Med*0.4) + (Lng*0.4)</span>
          </li>
          <li>
            <span class="label">Pressure Points</span>
            <span class="desc">Clutch & Mental Toughness</span>
            <span class="formula">(BP*0.5) + (Ret*0.3) + Bonus(+5)</span>
          </li>
        </ul>
      </div>

      <!-- Charts -->
      <div class="chart-container" :class="{ 'full-width': selectedChart !== 'radar' }">
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
  </div>
</template>

<style scoped>
.stats-chart {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.header-row {
  display: flex;
  margin-bottom: var(--space-6);
}

.content-grid {
  display: flex;
  gap: var(--space-6);
  align-items: center;
}

@media (max-width: 768px) {
  .content-grid {
    flex-direction: column-reverse; /* Chart on top on mobile */
  }
}

.chart-legend {
  flex: 1;
  min-width: 200px;
  max-width: 300px;
  background: var(--color-bg-secondary);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.chart-legend h3 {
  font-size: var(--font-size-sm);
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-3);
  letter-spacing: 0.05em;
}

.legend-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.legend-list li {
  display: flex;
  flex-direction: column;
}

.legend-list .label {
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.legend-list .desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-top: 2px;
}

.chart-container {
  flex: 2;
  max-width: 500px;
  margin: 0 auto;
}

.chart-container.full-width {
  flex: 1;
  max-width: 100%;
}

.chart-selector {
  display: flex;
  gap: var(--space-2);
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
  cursor: pointer;
}

.chart-btn:hover {
  background: var(--color-bg-hover);
}

.chart-btn.active {
  background: var(--color-accent);
  color: white;
  border-color: var(--color-accent);
}
</style>
