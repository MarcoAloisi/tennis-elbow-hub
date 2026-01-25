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
})

function handleRefresh() {
  store.fetchScores()
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
      
      <div class="header-stats">
        <div class="stat-item">
          <span class="stat-value">{{ store.serverCount }}</span>
          <span class="stat-label">Matches</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ store.activeMatchCount }}</span>
          <span class="stat-label">Live</span>
        </div>
        <div class="connection-status" :class="{ connected: isConnected }">
          <span class="status-dot"></span>
          {{ isConnected ? 'Live' : 'Connecting...' }}
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
  align-items: flex-start;
  margin-bottom: var(--space-6);
}

.header-content h1 {
  margin-bottom: var(--space-2);
}

.header-content p {
  color: var(--color-text-muted);
}

.header-stats {
  display: flex;
  align-items: center;
  gap: var(--space-6);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}

.stat-value {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-accent);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.connection-status.connected {
  color: var(--color-success);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-muted);
}

.connection-status.connected .status-dot {
  background: var(--color-success);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
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

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: var(--space-4);
  }
  
  .header-stats {
    width: 100%;
    justify-content: space-between;
  }
  
  .matches-grid {
    grid-template-columns: 1fr;
  }
}
</style>
