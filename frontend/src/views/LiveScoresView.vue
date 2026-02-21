<script setup>
import { onMounted, watch } from 'vue'
import { useScoresStore } from '@/stores/scores'
import { useWebSocket } from '@/composables/useWebSocket'
import { wsUrl } from '@/config/api'
import MatchCard from '@/components/scores/MatchCard.vue'
import FilterBar from '@/components/scores/FilterBar.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'

const store = useScoresStore()

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

function handleFilterUpdate(newFilters) {
  Object.keys(newFilters).forEach(key => {
    store.setFilter(key, newFilters[key])
  })
}

function formatTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleTimeString()
}
</script>

<template>
  <div class="live-scores-view">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <h1>Live Scores</h1>
        <p>Real-time Tennis Elbow 4 match scores</p>
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

    <!-- Monthly Stats & Top Players Section -->
    <div class="monthly-overview-section" v-if="store.monthlyStats.days_recorded > 0 || store.topPlayers.length > 0">
      
      <!-- Top 5 Players Card -->
      <div class="overview-card top-players-card">
        <div class="card-header">
          <h3>Top most active players</h3>
        </div>
        <div class="card-content">
          <table class="simple-table" v-if="store.topPlayers.length > 0">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Player</th>
                <th class="text-right">Matches</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(player, index) in store.topPlayers" :key="player.name">
                <td class="rank-col">#{{ index + 1 }}</td>
                <td class="player-col">{{ player.name }}</td>
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
          <h3>Daily Averages (This Month)</h3>
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
          </table>
        </div>
      </div>

    </div>

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
      @dismiss="store.error = null"
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
      <div class="empty-icon">🎾</div>
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
        :key="server.creation_time_ms"
        :server="server"
      />
    </div>

    <!-- Last updated -->
    <div v-if="store.lastUpdated" class="last-updated">
      Last updated: {{ formatTime(store.lastUpdated) }}
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
  justify-content: space-between;
  align-items: center; 
  margin-bottom: var(--space-10); /* Drastically increased spacing */
  padding-top: var(--space-8); /* Increased top padding */
}

.header-content h1 {
  margin-bottom: var(--space-3); /* Increased spacing below title */
  font-size: 3rem; /* Increased for impact */
  letter-spacing: -0.03em;
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
  background: rgba(34, 197, 94, 0.1);
  color: var(--color-success);
  border-color: rgba(34, 197, 94, 0.2);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-muted);
}

.connection-pill.connected .status-dot {
  background: var(--color-error);
  box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
  animation: pulse-red 2s infinite;
}

@keyframes pulse-red {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
  }
  
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 6px rgba(239, 68, 68, 0);
  }
  
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
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

.empty-icon {
  font-size: 4rem;
  margin-bottom: var(--space-4);
  opacity: 0.5;
}

.empty-state h3 {
  margin-bottom: var(--space-2);
}

.empty-state p {
  color: var(--color-text-muted);
  max-width: 300px;
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
  background: rgba(0, 0, 0, 0.02);
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

.text-right { text-align: right; }
.text-center { text-align: center; }
.text-muted { color: var(--color-text-muted); padding: var(--space-4) var(--space-5); }
.font-bold { font-weight: 700; color: var(--color-brand-live); }

.rank-col { width: 60px; color: var(--color-text-muted); font-weight: 600; }
.player-col { font-weight: 600; color: var(--color-text-primary); }
.matches-col { font-weight: 700; color: var(--color-brand-primary); }
.mod-name { font-weight: 600; }


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

  /* Make stats cards consistent full width on mobile */
  .single-stat-card,
  .stats-breakdown {
    width: 100%;
    justify-content: space-between;
  }

  /* Keep Single stat card centered internally or adjust if needed */
  .single-stat-card {
    flex-direction: row;
    gap: var(--space-4);
    justify-content: center;
  }
  
  .matches-grid {
    grid-template-columns: 1fr;
  }
  
  .monthly-overview-section {
    grid-template-columns: 1fr;
  }
}
</style>
