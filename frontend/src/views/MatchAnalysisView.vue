<script setup>
import { ref } from 'vue'
import { useAnalysisStore } from '@/stores/analysis'
import FileUploader from '@/components/analysis/FileUploader.vue'
import StatsTable from '@/components/analysis/StatsTable.vue'
import StatsChart from '@/components/analysis/StatsChart.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'

const store = useAnalysisStore()
const activeTab = ref('table')
const selectedCategory = ref('all')

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
    <div v-if="!store.hasAnalysis" class="upload-section">
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
      <!-- Match Info Header -->
      <div class="match-info-card">
        <div class="match-info-header">
          <button class="btn btn-ghost" @click="store.clearAnalysis">
            ← Back to Upload
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
</style>
