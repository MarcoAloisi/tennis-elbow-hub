<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import RealTennisScores from '@/components/real-tennis/RealTennisScores.vue'
import { useScoresStore } from '@/stores/scores'
import { useAuthStore } from '@/stores/auth'
import { useWebSocket } from '@/composables/useWebSocket'
import { useModalAccessibility } from '@/composables/useModalAccessibility'
import { wsUrl } from '@/config/api'
import MatchCard from '@/components/scores/MatchCard.vue'
import FilterBar from '@/components/scores/FilterBar.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import MonthlyOverview from '@/components/scores/MonthlyOverview.vue'
import PlayerDetailsModal from '@/components/players/PlayerDetailsModal.vue'
import { Activity } from 'lucide-vue-next'

const store = useScoresStore()
const authStore = useAuthStore()
const activeTab = ref<'te4' | 'real'>('te4')
const showDetails = ref(false)
const detailsName = ref('')
const detailsElo = ref(0)
const showSignupPrompt = ref(false)
const signupPlayerName = ref('')

useModalAccessibility(showSignupPrompt, {
  onClose: () => { showSignupPrompt.value = false },
  containerSelector: '#live-signup-prompt',
})

// WebSocket for real-time updates
const { data: wsData, isConnected, error: wsError } = useWebSocket(wsUrl('/api/scores/ws'))

// Update store when WebSocket receives data
watch(wsData, (newData) => {
  if (newData) {
    store.updateFromWebSocket(newData)
  }
})

// Initial fetch
onMounted(() => {
  store.fetchScores()
  store.fetchDailyStats()
  store.fetchMonthlyStats()
  store.fetchTopPlayers()
})

function handleRefresh() {
  store.fetchScores()
  store.fetchDailyStats()
  store.fetchMonthlyStats()
  store.fetchTopPlayers()
}

function handleFilterUpdate(newFilters: any) {
  Object.keys(newFilters).forEach(key => {
    store.setFilter(key as any, newFilters[key])
  })
}

function formatTime(isoString: string) {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleTimeString()
}

function onSelectPlayer(payload: { name: string; elo: number }) {
  if (authStore.loading) return
  if (!authStore.user) {
    signupPlayerName.value = payload.name
    showDetails.value = false
    showSignupPrompt.value = true
    return
  }
  showSignupPrompt.value = false
  detailsName.value = payload.name
  detailsElo.value = payload.elo
  showDetails.value = true
}
</script>

<template>
  <div class="live-scores-view">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <h1>Live Scores</h1>
        <p>Real-time Tennis Elbow 4 match scores</p>
        <p class="intro-text">
          Matches update live over WebSocket — no refresh needed. Each card shows ELO, surface, score, and duration.
          The win probability bar updates as the match plays out; click it for head-to-head form, or click a
          player's name for their full match history.
        </p>
      </div>
      
      <div class="header-right">
        <div class="stats-group">
          <!-- Today's Finished Matches -->
          <div class="single-stat-card">
              <span class="stat-value">{{ store.dailyStatsTotal }}</span>
              <span class="stat-label">Today</span>
          </div>

          <!-- Mod Breakdown Loop (skip 'date' key) -->
          <template v-for="(modStats, modName) in store.stats" :key="modName">
            <template v-if="modName !== 'date'">
              <div class="stat-divider"></div>
              
              <div class="stats-breakdown mod-group">
                <div class="mod-header">
                  <span class="mod-name">{{ modName }}</span>
                  <span class="mod-total">{{ modStats.total }}</span>
                </div>
                
                <div class="format-grid">
                  <div class="mini-stat-row" title="1 set">
                    <span class="mini-label-row">1s</span>
                    <span class="mini-val-row">{{ modStats.bo1 }}</span>
                  </div>
                  <div class="mini-stat-row" title="Best of 3">
                    <span class="mini-label-row">Bo3</span>
                    <span class="mini-val-row">{{ modStats.bo3 }}</span>
                  </div>
                  <div class="mini-stat-row" title="Best of 5">
                    <span class="mini-label-row">Bo5</span>
                    <span class="mini-val-row">{{ modStats.bo5 }}</span>
                  </div>
                </div>
              </div>
            </template>
          </template>
        </div>
        
        <div class="connection-pill" :class="{ connected: isConnected }">
          <span class="status-dot"></span>
          {{ isConnected ? 'Online' : 'Connecting...' }}
        </div>
      </div>
    </div>


    <!-- Tab switcher -->
    <div class="tab-switcher">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'te4' }"
        @click="activeTab = 'te4'"
      >
        TE4 Live
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'real' }"
        @click="activeTab = 'real'"
      >
        Real Tennis
      </button>
    </div>

    <!-- TE4 content -->
    <template v-if="activeTab === 'te4'">
      <!-- Monthly Stats & Top Players Section -->
      <MonthlyOverview />

      <!-- Filters -->
      <FilterBar
        :filters="store.filters"
        @update:filters="handleFilterUpdate"
        @refresh="handleRefresh"
      />

      <!-- Error state -->
      <ErrorAlert
        v-if="store.error || wsError"
        :message="store.error || wsError"
        type="error"
        @dismiss="store.clearError()"
      />

      <!-- Loading state -->
      <div v-if="store.isLoading && !store.servers.length" class="loading-state">
        <LoadingSpinner size="lg" />
        <p>Loading matches...</p>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="!store.filteredServers.length"
        class="empty-state"
      >
        <div class="empty-icon-wrapper">
          <Activity class="empty-icon" :size="64" :stroke-width="1.5" />
        </div>
        <h3>No matches found</h3>
        <p v-if="store.filters.searchQuery || store.filters.surface || store.filters.startedOnly">
          Try adjusting your filters
        </p>
        <p v-else>
          No live matches at the moment. Check back later!
        </p>
      </div>

      <!-- Match grid -->
      <div v-else class="matches-grid">
        <MatchCard
          v-for="server in store.filteredServers"
          :key="server.match_id"
          :server="server"
          @select-player="onSelectPlayer"
        />
      </div>

      <!-- Last updated -->
      <div v-if="store.lastUpdated" class="last-updated">
        Last updated: {{ formatTime(store.lastUpdated) }}
      </div>
    </template>

    <!-- Real Tennis content -->
    <RealTennisScores v-else />

    <PlayerDetailsModal
      :open="showDetails"
      :name="detailsName"
      :elo="detailsElo"
      @close="showDetails = false"
    />

    <div
      v-if="showSignupPrompt"
      id="live-signup-prompt"
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Sign up to see player stats"
      @click.self="showSignupPrompt = false"
    >
      <div class="signup-prompt-card">
        <h2>See stats for {{ signupPlayerName }}</h2>
        <p>Sign up to view wins, losses, and recent matches for this player.</p>
        <div class="signup-prompt-actions">
          <RouterLink to="/signup" class="btn btn-primary">Sign up</RouterLink>
          <RouterLink to="/login" class="btn btn-secondary">Log in</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.live-scores-view {
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-10);
  padding-top: var(--space-8);
}

.header-right {
  margin-top: var(--space-1);
}

.header-content h1 {
  margin-bottom: var(--space-3); /* Increased spacing below title */
  font-size: 3rem; /* Increased for impact */
  letter-spacing: -0.03em;
}

.header-content .intro-text {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  max-width: 65ch;
  margin-top: var(--space-2);
  line-height: 1.6;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-6);
}

.stats-group {
  display: flex;
  gap: var(--space-4);
}

.single-stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-2) var(--space-4);
  min-width: 80px;
  box-shadow: var(--shadow-sm);
}

.stat-divider {
  width: 1px;
  background-color: var(--color-border);
  height: 48px; /* Increased height for content */
  align-self: center;
}

.stats-breakdown {
  display: flex;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-2) var(--space-3);
  box-shadow: var(--shadow-sm);
  gap: var(--space-3);
}

.mod-group {
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
}

.mod-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 2px;
  margin-bottom: 2px;
}

.mod-name {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-text-secondary);
}

.mod-total {
  font-size: 0.8rem;
  font-weight: var(--font-weight-bold);
  color: var(--color-brand-live);
  margin-left: auto;
}

.format-grid {
  display: flex;
  gap: var(--space-3);
}

.mini-stat-row {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.mini-label-row {
  font-size: 0.6rem;
  color: var(--color-text-muted);
}

.mini-val-row {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.stat-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-brand-live); /* Use Live color for numbers */
  line-height: 1.2;
}

.stat-label {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.connection-pill {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  border: 1px solid transparent;
}

.connection-pill.connected {
  background: var(--color-success-light);
  color: var(--color-success);
  border-color: var(--color-success-border);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-muted);
}

.connection-pill.connected .status-dot {
  background: var(--color-success);
  box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
  animation: pulse-green 2s infinite;
}

@keyframes pulse-green {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
  }
  
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 6px rgba(34, 197, 94, 0);
  }
  
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
  }
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-16);
  gap: var(--space-4);
  color: var(--color-text-muted);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-16);
  text-align: center;
}

.empty-state h3 {
  margin-bottom: var(--space-2);
}

.empty-state p {
  color: var(--color-text-muted);
  max-width: 300px;
}

.empty-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  margin-bottom: var(--space-6);
  box-shadow: 0 0 20px rgba(34, 197, 94, 0.2);
}

[data-theme="dark"] .empty-icon-wrapper {
  color: var(--color-brand-primary);
  background: rgba(212, 255, 95, 0.1);
  box-shadow: 0 0 20px rgba(212, 255, 95, 0.15);
}

.matches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
}

.last-updated {
  margin-top: var(--space-6);
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}


@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: var(--space-6);
  }

  .header-content {
    text-align: center;
  }
  
  .header-right {
    width: 100%;
    flex-direction: column;
    gap: var(--space-4);
  }

  .stats-group {
    flex-direction: column;
    width: 100%;
    gap: var(--space-3);
  }

  .stat-divider {
    display: none;
  }

  .single-stat-card,
  .stats-breakdown {
    width: 100%;
    justify-content: space-between;
  }

  .single-stat-card {
    flex-direction: row;
    gap: var(--space-4);
    justify-content: center;
  }
  
  .matches-grid {
    grid-template-columns: 1fr;
  }
}

/* Tab switcher */
.tab-switcher {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-2);
}

.tab-btn {
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-full);
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all var(--transition-base);
  letter-spacing: 0.02em;
}

.tab-btn:hover {
  color: var(--color-text-primary);
  border-color: var(--color-border);
}

.tab-btn.active {
  color: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
  background: var(--color-bg-secondary);
}

.signup-prompt-card {
  padding: var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.signup-prompt-actions {
  display: flex;
  gap: var(--space-3);
}

.signup-prompt-actions a {
  text-decoration: none;
}

</style>
