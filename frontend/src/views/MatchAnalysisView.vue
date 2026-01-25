<script setup>
import { ref, computed } from 'vue'
import { useAnalysisStore } from '@/stores/analysis'
import FileUploader from '@/components/analysis/FileUploader.vue'
import StatsTable from '@/components/analysis/StatsTable.vue'
import StatsChart from '@/components/analysis/StatsChart.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'

const store = useAnalysisStore()
const viewMode = ref('dashboard') // 'dashboard' or 'detail'
const activeTab = ref('table')
const selectedCategory = ref('all')
const showAllStats = ref(false)

// Watch for match selection to switch view
function openMatch(index) {
  store.selectMatch(index)
  viewMode.value = 'detail'
}

function backToDashboard() {
  viewMode.value = 'dashboard'
}

// Stats mapping for the aggregate table
const aggregatedPlayerStats = computed(() => {
    const s = store.aggregateStats
    if (!s) return null
    
    // Helper to extract value since we flattened the structure in store
    // Use optional chaining or defaults as safety
    return {
        serve: {
            first_serve_pct: s.first_serve_pct,
            aces: s.aces,
            double_faults: s.double_faults,
            fastest_serve_kmh: s.fastest_serve,
            avg_first_serve_kmh: s.avg_first_serve,
            avg_second_serve_kmh: s.avg_second_serve,
            first_serve_in: 0, // No total for aggregates
            first_serve_total: 0
        },
        rally: {
            short_rallies_won: s.short_rally_won_pct,
            short_rallies_total: 0, // Using pct directly
            normal_rallies_won: s.medium_rally_won_pct,
            normal_rallies_total: 0,
            long_rallies_won: s.long_rally_won_pct,
            long_rallies_total: 0,
            avg_rally_length: s.avg_rally_length
        },
        points: {
            winners: s.winners,
            forced_errors: s.forced_errors,
            unforced_errors: s.unforced_errors,
            points_on_first_serve_won: s.first_serve_won_pct,
            points_on_first_serve_total: 0, // pct
            points_on_second_serve_won: s.second_serve_won_pct,
            points_on_second_serve_total: 0,
            return_points_won: s.return_points_won_pct,
            return_points_total: 0,
            return_winners: s.return_winners,
            net_points_won: s.net_points_won_pct,
            net_points_total: 0,
            total_points_won: s.total_points_won_pct
        },
        break_points: {
            break_points_won: s.break_points_won_pct,
            break_points_total: 0,
            break_games_won: s.break_games_won_pct,
            break_games_total: 0,
            set_points_saved: s.set_points_saved,
            match_points_saved: s.match_points_saved
        }
    }
})

const categories = [
  { value: 'all', label: 'All Stats' },
  { value: 'serve', label: 'Serve' },
  { value: 'rally', label: 'Rally' },
  { value: 'points', label: 'Points' },
  { value: 'break_points', label: 'Break Points' }
]

async function handleUpload(file) {
  try {
    await store.uploadAndAnalyze(file)
  } catch (e) {
    // Error is already in store
  }
}

async function loadSample() {
  await store.loadSampleAnalysis()
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<template>
  <div class="analysis-view">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <h1>Match Analysis</h1>
        <p>Upload your Tennis Elbow 4 match logs for detailed statistics</p>
      </div>
    </div>

    <!-- Error Alert -->
    <ErrorAlert 
      v-if="store.error"
      :message="store.error"
      type="error"
      @dismiss="store.error = null"
    />

    <!-- Upload Section (shown when no analysis) -->
    <div v-if="!store.hasMatches" class="upload-section">
      <FileUploader 
        :is-loading="store.isLoading"
        @upload="handleUpload"
      />
      
      <div class="sample-action">
        <span class="divider-text">or</span>
        <button class="btn btn-secondary" @click="loadSample" :disabled="store.isLoading">
          📊 Load Sample Match
        </button>
      </div>
    </div>

    <!-- Analysis Results -->
    <div v-else class="analysis-results">
        
      <!-- DASHBOARD MODE -->
      <div v-if="viewMode === 'dashboard'" class="dashboard-container">
        <!-- Dashboard Header -->
        <div class="dashboard-header">
            <div class="header-left">
                <button class="btn btn-ghost" @click="store.clearAnalysis">← Upload New File</button>
                <h2>Career Dashboard</h2>
            </div>
            
            <!-- Filters -->
            <div class="filters-bar">
                <div class="filter-group">
                    <label class="filter-label">Search</label>
                    <input 
                        v-model="store.filters.opponent" 
                        placeholder="Opponent..." 
                        class="filter-input"
                    />
                </div>

                <div class="filter-group">
                    <label class="filter-label">Date Range</label>
                    <div class="date-inputs">
                        <input type="date" v-model="store.filters.dateStart" class="filter-input date-input" />
                        <span>to</span>
                        <input type="date" v-model="store.filters.dateEnd" class="filter-input date-input" />
                    </div>
                </div>

                <div class="filter-group">
                    <label class="filter-label">Filters</label>
                    <div class="select-group">
                        <select v-model="store.filters.surface" class="filter-select">
                            <option :value="null">All Surfaces</option>
                            <option value="Hard">Hard</option>
                            <option value="Clay">Clay</option>
                            <option value="Grass">Grass</option>
                            <option value="Indoor">Indoor</option>
                        </select>
                        <select v-model="store.filters.sets" class="filter-select">
                            <option :value="null">All Sets</option>
                            <option value="1">1 Set</option>
                            <option value="3">Best of 3</option>
                            <option value="5">Best of 5</option>
                        </select>
                    </div>
                </div>

                <div class="filter-group options-group">
                    <label class="checkbox-label">
                        <input type="checkbox" v-model="store.filters.cpu" />
                        <span>Hide CPU</span>
                    </label>
                    <button class="btn btn-sm" @click="store.sortDesc = !store.sortDesc">
                        {{ store.sortDesc ? '⬇️ Newest' : '⬆️ Oldest' }}
                    </button>
                </div>
            </div>
        </div>

        <!-- Global Stats Section -->
        <div class="global-stats-section" v-if="store.aggregateStats">
             <div class="section-header">
                <h3>Global Statistics ({{ store.aggregateStats.totalMatches }} Matches)</h3>
                <div class="stats-controls">
                     <div class="mode-toggle">
                        <button 
                            class="mode-btn" 
                            :class="{ active: store.statsMode === 'avg' }"
                            @click="store.statsMode = 'avg'"
                        >Average</button>
                        <button 
                            class="mode-btn" 
                            :class="{ active: store.statsMode === 'median' }"
                            @click="store.statsMode = 'median'"
                        >Median</button>
                    </div>
                    <button class="btn btn-secondary" @click="showAllStats = !showAllStats">
                        {{ showAllStats ? 'Hide All Stats' : 'Show All Stats' }}
                    </button>
                </div>
             </div>

             <!-- Summary Cards -->
             <div class="stats-overview">
                <div class="stat-card">
                    <div class="stat-value">{{ store.aggregateStats.avgWinners }}</div>
                    <div class="stat-label">{{ store.statsMode === 'avg' ? 'Avg' : 'Median' }} Winners</div>
                </div>
                 <div class="stat-card">
                    <div class="stat-value">{{ store.aggregateStats.avgUnforcedErrors }}</div>
                    <div class="stat-label">{{ store.statsMode === 'avg' ? 'Avg' : 'Median' }} Errors</div>
                </div>
                 <div class="stat-card">
                    <div class="stat-value">{{ store.aggregateStats.avgAces }}</div>
                    <div class="stat-label">{{ store.statsMode === 'avg' ? 'Avg' : 'Median' }} Aces</div>
                </div>
                 <div class="stat-card">
                    <div class="stat-value">{{ store.aggregateStats.avgDoubleFaults }}</div>
                    <div class="stat-label">{{ store.statsMode === 'avg' ? 'Avg' : 'Median' }} D.Faults</div>
                </div>
            </div>
            
            <!-- Full Extended Stats Table -->
            <div v-if="showAllStats" class="extended-stats-container">
                <StatsTable 
                    :player1="aggregatedPlayerStats"
                    :player2="{ serve:{}, rally:{}, points:{}, break_points:{} }"
                    category="all"
                />
            </div>
        </div>

        <!-- Match List Table -->
        <div class="match-list-container">
            <table class="match-table">
                <thead>
                    <tr>
                        <th style="width: 15%">Date</th>
                        <th style="width: 20%">Tournament</th>
                        <th style="width: 30%">Opponent</th>
                        <th style="width: 15%">Score</th>
                        <th style="width: 10%">Duration</th>
                        <th style="width: 10%">Action</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(match, index) in store.filteredMatches" :key="index" @click="openMatch(store.matches.indexOf(match))" class="clickable-row">
                        <td>
                            <div class="date-cell">
                                <span class="date-date">{{ formatDate(match.info?.date).split(',')[0] }}</span>
                                <span class="date-time">{{ formatDate(match.info?.date).split(',')[1] }}</span>
                            </div>
                        </td>
                        <td>{{ match.info?.tournament }}</td>
                        <td>
                            <div class="opponent-cell">
                                {{ match.player1.name === 'Player 1' ? match.player2.name : (match.player1.name === 'Player' ? match.player2.name : match.player1.name) }} 
                                <span class="vs-badge">vs</span> 
                                {{ match.player2.name }}
                            </div>
                        </td> 
                        <td class="score-cell">{{ match.info?.score }}</td>
                        <td>{{ match.info?.duration }}</td>
                        <td><button class="btn btn-sm btn-primary">View</button></td>
                    </tr>
                    <tr v-if="store.filteredMatches.length === 0">
                        <td colspan="6" class="text-center">No matches found matching filters</td>
                    </tr>
                </tbody>
            </table>
        </div>
      </div>

      <!-- DETAIL MODE -->
      <div v-else class="match-detail-view">
      <!-- Match Info Header -->
      <div class="match-info-card">
        <div class="match-info-header">
          <button class="btn btn-ghost" @click="backToDashboard">
            ← Back to Dashboard
          </button>
          <span class="badge badge-success">Analysis Complete</span>
        </div>
        
        <div class="match-info-content">
          <div class="players-display">
            <div class="player-side">
              <h2 class="player-name">{{ store.matchInfo?.player1_name }}</h2>
              <span class="player-label">Player 1</span>
            </div>
            <div class="vs-display">
              <span class="score-display">{{ store.matchInfo?.score }}</span>
              <span class="vs-text">vs</span>
            </div>
            <div class="player-side right">
              <h2 class="player-name">{{ store.matchInfo?.player2_name }}</h2>
              <span class="player-label">Player 2</span>
            </div>
          </div>
          
          <div class="match-meta">
            <span v-if="store.matchInfo?.tournament">
              🏆 {{ store.matchInfo.tournament }}
            </span>
            <span v-if="store.matchInfo?.duration">
              ⏱️ {{ store.matchInfo.duration }}
            </span>
            <span v-if="store.matchInfo?.date">
              📅 {{ formatDate(store.matchInfo.date) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Tab Navigation -->
      <div class="analysis-tabs">
        <button 
          class="tab-btn"
          :class="{ active: activeTab === 'table' }"
          @click="activeTab = 'table'"
        >
          📋 Statistics
        </button>
        <button 
          class="tab-btn"
          :class="{ active: activeTab === 'chart' }"
          @click="activeTab = 'chart'"
        >
          📊 Charts
        </button>
      </div>

      <!-- Tab Content: Statistics Table -->
      <div v-if="activeTab === 'table'" class="tab-content">
        <!-- Category Filter -->
        <div class="category-filter">
          <button 
            v-for="cat in categories"
            :key="cat.value"
            class="category-btn"
            :class="{ active: selectedCategory === cat.value }"
            @click="selectedCategory = cat.value"
          >
            {{ cat.label }}
          </button>
        </div>

        <div class="stats-container">
          <StatsTable 
            :player1="store.player1Stats"
            :player2="store.player2Stats"
            :category="selectedCategory"
          />
        </div>
      </div>

      <!-- Tab Content: Charts -->
      <div v-if="activeTab === 'chart'" class="tab-content">
        <StatsChart 
          :player1="store.player1Stats"
          :player2="store.player2Stats"
        />
      </div>

      <!-- Future ML Section Placeholder -->
      <div class="ml-section">
        <div class="ml-card">
          <div class="ml-icon">🤖</div>
          <h3>AI Insights Coming Soon</h3>
          <p>Machine learning analysis to predict performance, identify areas for improvement, and track progress over time.</p>
          <div class="ml-features">
            <span class="ml-feature">📈 Performance Predictions</span>
            <span class="ml-feature">🎯 Improvement Areas</span>
            <span class="ml-feature">📊 Trend Analysis</span>
          </div>
        </div>
      </div>
      </div>
      </div>
  </div>
</template>

<style scoped>
.analysis-view {
  min-height: 100%;
}

.page-header {
  margin-bottom: var(--space-8);
}

.page-header h1 {
  margin-bottom: var(--space-2);
}

.page-header p {
  color: var(--color-text-muted);
}

.upload-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 600px;
  margin: 0 auto;
}

.sample-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-6);
}

.divider-text {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

/* Analysis Results */
.analysis-results {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.match-info-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
}

.match-info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.match-info-content {
  text-align: center;
}

.players-display {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: var(--space-6);
  align-items: center;
  margin-bottom: var(--space-4);
}

.player-side {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.player-side.right {
  text-align: right;
}

.player-name {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
}

.player-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.vs-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}

.score-display {
  font-size: var(--font-size-xl);
  font-family: var(--font-mono);
  font-weight: var(--font-weight-bold);
  color: var(--color-accent);
}

.vs-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.match-meta {
  display: flex;
  justify-content: center;
  gap: var(--space-6);
  flex-wrap: wrap;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

/* Tabs */
.analysis-tabs {
  display: flex;
  gap: var(--space-2);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-2);
}

.tab-btn {
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  background: var(--color-bg-hover);
}

.tab-btn.active {
  background: var(--color-accent);
  color: white;
}

.tab-content {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

/* Category Filter */
.category-filter {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.category-btn {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  transition: all var(--transition-fast);
}

.category-btn:hover {
  background: var(--color-bg-hover);
}

.category-btn.active {
  background: var(--color-accent-light);
  color: var(--color-accent);
}

/* ML Section */
.ml-section {
  margin-top: var(--space-4);
}

.ml-card {
  background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-accent-light) 100%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  text-align: center;
}

.ml-icon {
  font-size: 3rem;
  margin-bottom: var(--space-4);
}

.ml-card h3 {
  margin-bottom: var(--space-2);
}

.ml-card p {
  color: var(--color-text-secondary);
  max-width: 500px;
  margin: 0 auto var(--space-4);
}

.ml-features {
  display: flex;
  justify-content: center;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.ml-feature {
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-primary);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
}

@media (max-width: 768px) {
  .players-display {
    grid-template-columns: 1fr;
    text-align: center;
  }
  
  .player-side.right {
    text-align: center;
  }
  
  .vs-display {
    order: -1;
  }
  
  .match-meta {
    flex-direction: column;
    gap: var(--space-2);
  }
}

/* Dashboard Styles */
.dashboard-container {
    display: flex;
    flex-direction: column;
    gap: var(--space-6);
}

.dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--space-4);
}

.filters-bar {
    display: flex;
    gap: var(--space-2);
}

.filter-input, .filter-select {
    padding: var(--space-2);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg-card);
}

.stats-overview {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: var(--space-4);
}

.stat-card {
    background: var(--color-bg-card);
    padding: var(--space-4);
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-border);
    text-align: center;
    box-shadow: var(--shadow-sm);
}

.stat-value {
    font-size: var(--font-size-2xl);
    font-weight: bold;
    color: var(--color-accent);
}

.stat-label {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
}

.match-table {
    width: 100%;
    border-collapse: collapse;
    background: var(--color-bg-card);
    border-radius: var(--radius-lg);
    overflow: hidden;
}

.match-table th, .match-table td {
    padding: var(--space-3);
    text-align: left;
    border-bottom: 1px solid var(--color-border);
}

.match-table th {
    background: var(--color-bg-secondary);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-secondary);
}

.clickable-row {
    cursor: pointer;
    transition: background-color var(--transition-fast);
}

.clickable-row:hover {
    background-color: var(--color-bg-hover);
}

.score-cell {
    font-family: var(--font-mono);
    font-weight: bold;
}

/* NEW STYLES */
.filter-group {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
}

.filter-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    font-weight: var(--font-weight-medium);
}

.date-inputs {
    display: flex;
    align-items: center;
    gap: var(--space-2);
}

.date-input {
    padding: var(--space-2);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg-card);
    font-size: var(--font-size-sm);
    max-width: 140px;
}

.select-group {
    display: flex;
    gap: var(--space-2);
}

.options-group {
    justify-content: flex-end;
    align-items: flex-end;
    gap: var(--space-2); 
    margin-left: auto;
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    cursor: pointer;
    user-select: none;
    margin-bottom: var(--space-2);
}

.global-stats-section {
    background: var(--color-bg-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-6);
    display: flex;
    flex-direction: column;
    gap: var(--space-6);
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.section-header h3 {
    margin: 0;
    font-size: var(--font-size-lg);
}

.stats-controls {
    display: flex;
    gap: var(--space-4);
    align-items: center;
}

.mode-toggle {
    display: flex;
    background: var(--color-bg-secondary);
    padding: 2px;
    border-radius: var(--radius-md);
}

.mode-btn {
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    transition: all var(--transition-fast);
}

.mode-btn.active {
    background: var(--color-bg-card);
    color: var(--color-accent);
    font-weight: var(--font-weight-medium);
    box-shadow: var(--shadow-sm);
}

.extended-stats-container {
    border-top: 1px solid var(--color-border);
    padding-top: var(--space-4);
}

/* Table Cell Styles */
.date-cell {
    display: flex;
    flex-direction: column;
}

.date-date {
    font-weight: var(--font-weight-medium);
}

.date-time {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
}

.opponent-cell {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-weight: var(--font-weight-medium);
}

.vs-badge {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    background: var(--color-bg-secondary);
    padding: 2px 6px;
    border-radius: var(--radius-sm);
}

</style>
