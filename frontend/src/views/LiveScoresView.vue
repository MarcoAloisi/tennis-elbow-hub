<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import ResultsTab from '@/components/scores/ResultsTab.vue'
import { useScoresStore, type MatchRef } from '@/stores/scores'
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
import MatchDetailModal from '@/components/scores/MatchDetailModal.vue'
import { Activity } from 'lucide-vue-next'

const store = useScoresStore()
const authStore = useAuthStore()
const activeTab = ref<'te4' | 'results'>('te4')
const showDetails = ref(false)
const detailsName = ref('')
const detailsElo = ref(0)
const detail = ref<MatchRef | null>(null)
const MOD_LABELS: Record<string, string> = { xkt: 'XKT', wtsl: 'WTSL' }

const liveCount = computed(() => store.servers.filter((s) => s.is_started).length)
const waitingCount = computed(() => store.servers.length - liveCount.value)
const modTotals = computed(() =>
  Object.entries(store.stats)
    .filter(([name]) => name !== 'date')
    .map(([name, m]) => ({
      name: MOD_LABELS[name] ?? name.charAt(0).toUpperCase() + name.slice(1),
      total: (m as any).total,
      title: `1 set ${(m as any).bo1}, Bo3 ${(m as any).bo3}, Bo5 ${(m as any).bo5}`,
    })),
)
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
    <div class="page-header">
      <div class="header-content">
        <h1>Live scores</h1>
        <p class="finding">
          <span><i class="dot" :class="{ on: isConnected }"></i><b>{{ liveCount }}</b> {{ liveCount === 1 ? 'match' : 'matches' }} live now</span>
          <span v-if="waitingCount > 0"><b>{{ waitingCount }}</b> waiting for an opponent</span>
          <span><b>{{ store.dailyStatsTotal }}</b> finished today</span>
          <span v-for="mod in modTotals" :key="mod.name" class="mod-total" :title="mod.title">
            {{ mod.name }} <b>{{ mod.total }}</b>
          </span>
          <span v-if="!isConnected" class="conn">Connecting…</span>
        </p>
      </div>

      <div class="tools">
        <div class="seg" role="group" aria-label="View">
          <button type="button" :aria-pressed="activeTab === 'te4'" @click="activeTab = 'te4'">TE4 live</button>
          <button type="button" :aria-pressed="activeTab === 'results'" @click="activeTab = 'results'">Results</button>
        </div>
      </div>
    </div>

    <!-- TE4 content -->
    <template v-if="activeTab === 'te4'">
      <FilterBar
        class="filters"
        :filters="store.filters"
        @update:filters="handleFilterUpdate"
        @refresh="handleRefresh"
      />

      <ErrorAlert
        v-if="store.error || wsError"
        :message="store.error || wsError"
        type="error"
        @dismiss="store.clearError()"
      />

      <div v-if="store.isLoading && !store.servers.length" class="loading-state">
        <LoadingSpinner size="lg" />
        <p>Loading matches...</p>
      </div>

      <div
        v-else-if="!store.filteredServers.length"
        class="empty-state"
      >
        <div class="empty-icon-wrapper">
          <Activity class="empty-icon" :size="40" :stroke-width="1.5" />
        </div>
        <h3>No matches found</h3>
        <p v-if="store.filters.searchQuery || store.filters.surface || store.filters.startedOnly">
          Try adjusting your filters
        </p>
        <p v-else>
          No live matches at the moment. Check back later!
        </p>
      </div>

      <div v-else class="matches-grid">
        <MatchCard
          v-for="server in store.filteredServers"
          :key="server.match_id"
          :server="server"
          @select-player="onSelectPlayer"
          @open-match-detail="detail = $event"
        />
      </div>

      <div v-if="store.lastUpdated" class="last-updated">
        Last updated {{ formatTime(store.lastUpdated) }}
      </div>

      <MonthlyOverview />

      <section class="how-it-works" aria-labelledby="how-heading">
        <h2 id="how-heading">How the board works</h2>
        <p class="intro-text">
          Matches update live over WebSocket, so the page needs no refresh. Each card shows ELO, surface, score, and duration.
          The win probability bar updates as the match plays out. Click it for head-to-head form, or click a
          player's name for their full match history.
        </p>
      </section>
    </template>

    <ResultsTab v-else @open-match-detail="detail = $event" />

    <PlayerDetailsModal
      :open="showDetails"
      :name="detailsName"
      :elo="detailsElo"
      @close="showDetails = false"
    />

    <MatchDetailModal
      :open="detail !== null"
      :match="detail"
      :live-server="store.servers.find((s) => s.match_id === detail?.matchId)"
      @close="detail = null"
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
  align-items: flex-end;
  flex-wrap: wrap;
  gap: var(--space-4) var(--space-6);
  margin-bottom: var(--space-4);
}

.header-content h1 {
  font-size: 2rem;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.finding {
  margin-top: var(--space-2);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1) var(--space-4);
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

.finding {
  font-variant-numeric: tabular-nums;
}

.finding b {
  color: var(--color-text-primary);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: var(--space-2);
  border-radius: 50%;
  background: var(--color-text-muted);
}

.dot.on {
  background: var(--color-brand-live);
  animation: live-pulse 2s ease-out infinite;
}

@keyframes live-pulse {
  0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.55); }
  70%, 100% { box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
}

.mod-total,
.conn {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.mod-total b {
  color: var(--color-text-secondary);
}

.conn {
  margin-left: auto;
}

.filters {
  margin-bottom: var(--space-4);
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
  padding: var(--space-16) var(--space-4);
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
  color: var(--color-text-muted);
  margin-bottom: var(--space-4);
}

.matches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--space-4);
}

.last-updated {
  margin-top: var(--space-4);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.how-it-works {
  margin-top: var(--space-12);
}

.how-it-works h2 {
  font-size: 1.25rem;
  letter-spacing: -0.01em;
}

.intro-text {
  margin-top: var(--space-3);
  max-width: 65ch;
  color: var(--color-text-secondary);
}

.tools .seg {
  display: inline-flex;
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  padding: 3px;
}

.tools .seg button {
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

.tools .seg button:hover {
  color: var(--color-text-primary);
}

.tools .seg button[aria-pressed="true"] {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.signup-prompt-card {
  padding: var(--space-6);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
}

.signup-prompt-actions {
  display: flex;
  gap: var(--space-3);
}

.signup-prompt-actions a {
  text-decoration: none;
}

@media (max-width: 768px) {
  .header-content h1 {
    font-size: 1.75rem;
  }

  .matches-grid {
    grid-template-columns: 1fr;
  }

  .conn {
    margin-left: 0;
  }
}
</style>
