<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRealTennis, type RealTennisMatch } from '@/composables/useRealTennis'
import RealMatchCard from './RealMatchCard.vue'
import TournamentCard from './TournamentCard.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { Activity } from 'lucide-vue-next'

const { live, upcoming, completed, tournaments, isLoading, error, stale, fetchScores } = useRealTennis()
const selectedTournamentId = ref<number | null>(null)

function filterByTournament(matches: RealTennisMatch[]): RealTennisMatch[] {
  if (selectedTournamentId.value === null) return matches
  return matches.filter(m => m.tournament.id === selectedTournamentId.value)
}

const filteredLive = computed(() => filterByTournament(live.value))
const filteredUpcoming = computed(() => filterByTournament(upcoming.value))
const filteredCompleted = computed(() => filterByTournament(completed.value))
const hasMatches = computed(
  () => filteredLive.value.length + filteredUpcoming.value.length + filteredCompleted.value.length > 0
)
</script>

<template>
  <div class="real-tennis-scores">
    <!-- Stale data warning -->
    <ErrorAlert
      v-if="stale"
      type="warning"
      message="Score data may be delayed — SofaScore temporarily unreachable"
      :dismissible="false"
    />

    <!-- Tournament filter row -->
    <div v-if="tournaments.length" class="tournament-filter-row">
      <button
        class="all-pill"
        :class="{ active: selectedTournamentId === null }"
        @click="selectedTournamentId = null"
      >
        All
      </button>
      <TournamentCard
        v-for="t in tournaments"
        :key="t.id"
        :tournament="t"
        :active="selectedTournamentId === t.id"
        @select="selectedTournamentId = $event"
      />
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="loading-state">
      <LoadingSpinner size="lg" />
      <p>Loading scores...</p>
    </div>

    <!-- Error state (no data at all) -->
    <ErrorAlert
      v-else-if="error && !hasMatches"
      :message="error"
      type="error"
      @dismiss="fetchScores()"
    />

    <!-- Empty state -->
    <div v-else-if="!hasMatches" class="empty-state">
      <div class="empty-icon-wrapper">
        <Activity :size="64" :stroke-width="1.5" />
      </div>
      <h3>No matches today</h3>
      <p>Check back during a tournament day</p>
    </div>

    <!-- Match sections -->
    <template v-else>
      <div v-if="filteredLive.length" class="match-section">
        <h3 class="section-label">
          <span class="section-dot"></span>
          Live Now
        </h3>
        <div class="matches-grid">
          <RealMatchCard v-for="m in filteredLive" :key="m.id" :match="m" />
        </div>
      </div>

      <div v-if="filteredUpcoming.length" class="match-section">
        <h3 class="section-label">Today's Schedule</h3>
        <div class="matches-grid">
          <RealMatchCard v-for="m in filteredUpcoming" :key="m.id" :match="m" />
        </div>
      </div>

      <div v-if="filteredCompleted.length" class="match-section">
        <h3 class="section-label">Completed</h3>
        <div class="matches-grid">
          <RealMatchCard v-for="m in filteredCompleted" :key="m.id" :match="m" />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.real-tennis-scores {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.tournament-filter-row {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  padding-bottom: var(--space-2);
  scrollbar-width: thin;
}

.all-pill {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-base);
}

.all-pill:hover,
.all-pill.active {
  border-color: var(--color-brand-primary);
  color: var(--color-brand-primary);
}

.match-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.section-label {
  font-size: var(--font-size-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.section-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-brand-live);
  box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
  animation: pulse-green 2s infinite;
}

@keyframes pulse-green {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(34, 197, 94, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
}

.matches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
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

.empty-state h3 {
  margin-bottom: var(--space-2);
}

.empty-state p {
  color: var(--color-text-muted);
  max-width: 300px;
}

@media (max-width: 768px) {
  .matches-grid {
    grid-template-columns: 1fr;
  }
}
</style>
