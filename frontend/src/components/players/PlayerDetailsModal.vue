<script setup lang="ts">
import { watch, toRef } from 'vue'
import { usePlayerDetails } from '@/composables/usePlayerDetails'
import { useModalAccessibility } from '@/composables/useModalAccessibility'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { X, Trophy, Target, BarChart3, Hash, Calendar, Activity } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  name: string
  elo: number
}>()

const emit = defineEmits<{ close: [] }>()

const {
  details: playerDetails,
  isLoading: playerDetailsLoading,
  error: playerDetailsError,
  fetchPlayerDetails,
  clearDetails,
} = usePlayerDetails()

useModalAccessibility(toRef(props, 'open'), {
  onClose: () => emit('close'),
  containerSelector: '#player-details-dialog',
})

watch(
  () => [props.open, props.name, props.elo] as const,
  ([open, playerName, elo]) => {
    if (!open || !elo || elo <= 0) {
      clearDetails()
      return
    }
    fetchPlayerDetails(playerName, elo)
  }
)

function formatDate(isoString: string | null): string {
  if (!isoString) return '—'
  return new Date(isoString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
</script>

<template>
  <div
    v-if="open"
    id="player-details-dialog"
    class="modal-overlay player-details-overlay"
    role="dialog"
    aria-modal="true"
    aria-label="Player details"
    @click.self="emit('close')"
  >
    <div class="player-modal">
      <div class="player-modal-header">
        <h2>{{ playerDetails?.name || name }}</h2>
        <button class="modal-close" aria-label="Close" @click="emit('close')">
          <X :size="20" />
        </button>
      </div>

      <div v-if="playerDetailsLoading" class="modal-loading">
        <LoadingSpinner size="md" />
        <p>Loading player data…</p>
      </div>

      <div v-else-if="playerDetailsError" class="modal-error">
        <p>{{ playerDetailsError }}</p>
      </div>

      <div
        v-else-if="!playerDetails || playerDetails.total_matches === 0"
        class="modal-error"
      >
        <p>No recorded matches yet.</p>
      </div>

      <div v-else-if="playerDetails" class="player-modal-body">
          <div class="detail-stats-grid">
            <div class="detail-stat">
              <Trophy :size="18" class="detail-stat-icon win" />
              <div class="detail-stat-content">
                <span class="detail-stat-value">{{ playerDetails.wins }}</span>
                <span class="detail-stat-label">Wins</span>
              </div>
            </div>
            <div class="detail-stat">
              <Target :size="18" class="detail-stat-icon loss" />
              <div class="detail-stat-content">
                <span class="detail-stat-value">{{ playerDetails.losses }}</span>
                <span class="detail-stat-label">Losses</span>
              </div>
            </div>
            <div class="detail-stat">
              <BarChart3 :size="18" class="detail-stat-icon rate" />
              <div class="detail-stat-content">
                <span class="detail-stat-value">{{ playerDetails.win_rate }}%</span>
                <span class="detail-stat-label">Win Rate</span>
              </div>
            </div>
            <div class="detail-stat">
              <Hash :size="18" class="detail-stat-icon total" />
              <div class="detail-stat-content">
                <span class="detail-stat-value">{{ playerDetails.total_matches }}</span>
                <span class="detail-stat-label">Total</span>
              </div>
            </div>
          </div>
          <div class="detail-section">
            <h3><Activity :size="16" /> Recent Activity</h3>
            <div class="activity-pills">
              <span class="activity-pill">
                <strong>{{ playerDetails.matches_last_7_days }}</strong> matches last 7 days
              </span>
              <span class="activity-pill">
                <strong>{{ playerDetails.matches_last_30_days }}</strong> matches last 30 days
              </span>
            </div>
          </div>
          <div class="detail-section" v-if="playerDetails.best_win">
            <h3><Trophy :size="16" /> Best Win</h3>
            <div class="highlight-match win-highlight">
              <span class="match-result-badge W">W</span>
              <div class="match-info">
                <span class="match-opponent">vs {{ playerDetails.best_win.opponent }}</span>
                <span class="match-score">{{ playerDetails.best_win.score }}</span>
              </div>
              <span class="match-elo" v-if="playerDetails.best_win.opponent_elo">ELO {{ playerDetails.best_win.opponent_elo }}</span>
              <span class="match-date" v-if="playerDetails.best_win.date">{{ formatDate(playerDetails.best_win.date) }}</span>
            </div>
          </div>
          <div class="detail-section" v-if="playerDetails.worst_loss">
            <h3><Target :size="16" /> Worst Loss</h3>
            <div class="highlight-match loss-highlight">
              <span class="match-result-badge L">L</span>
              <div class="match-info">
                <span class="match-opponent">vs {{ playerDetails.worst_loss.opponent }}</span>
                <span class="match-score">{{ playerDetails.worst_loss.score }}</span>
              </div>
              <span class="match-elo" v-if="playerDetails.worst_loss.opponent_elo">ELO {{ playerDetails.worst_loss.opponent_elo }}</span>
              <span class="match-date" v-if="playerDetails.worst_loss.date">{{ formatDate(playerDetails.worst_loss.date) }}</span>
            </div>
          </div>
          <div class="detail-section" v-if="playerDetails.recent_matches?.length">
            <h3><Calendar :size="16" /> Last {{ playerDetails.recent_matches.length }} Matches</h3>
            <div class="recent-matches-list">
              <div class="recent-match" v-for="(match, i) in playerDetails.recent_matches" :key="i">
                <span class="match-result-badge" :class="match.result">{{ match.result }}</span>
                <span class="recent-opponent">{{ match.opponent }}</span>
                <span class="recent-score">{{ match.score ?? '—' }}</span>
                <span class="recent-elo" v-if="match.opponent_elo">{{ match.opponent_elo }}</span>
                <span class="recent-date">{{ formatDate(match.date) }}</span>
              </div>
            </div>
          </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.player-details-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(6px);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  z-index: var(--z-modal, 1000);
  padding: var(--space-8) var(--space-4);
  overflow-y: auto;
}

.player-modal {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 580px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: modalSlideIn 0.25s ease-out;
  overflow: hidden;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-16px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.player-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.player-modal-header h2 {
  font-size: 1.3rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--color-text-primary);
  margin: 0;
}

.modal-close {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.modal-close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.modal-loading,
.modal-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12);
  gap: var(--space-3);
  color: var(--color-text-muted);
}

.modal-error {
  color: var(--color-error);
}

.player-modal-body {
  padding: var(--space-5) var(--space-6);
  max-height: 70vh;
  overflow-y: auto;
}

/* Stats Grid */
.detail-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.detail-stat {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.detail-stat-icon {
  flex-shrink: 0;
}

.detail-stat-icon.win { color: #22c55e; }
.detail-stat-icon.loss { color: #ef4444; }
.detail-stat-icon.rate { color: #3b82f6; }
.detail-stat-icon.total { color: #f59e0b; }

.detail-stat-content {
  display: flex;
  flex-direction: column;
}

.detail-stat-value {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--color-text-primary);
  line-height: 1.1;
}

.detail-stat-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
  color: var(--color-text-muted);
}

/* Sections */
.detail-section {
  margin-bottom: var(--space-5);
}

.detail-section h3 {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-3);
}

/* Activity Pills */
.activity-pills {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.activity-pill {
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  font-size: 0.82rem;
  color: var(--color-text-secondary);
}

.activity-pill strong {
  color: var(--color-text-primary);
  font-weight: 700;
}

/* Highlight Match Cards */
.highlight-match {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid;
}

.win-highlight {
  background: rgba(34, 197, 94, 0.06);
  border-color: rgba(34, 197, 94, 0.2);
}

.loss-highlight {
  background: rgba(239, 68, 68, 0.06);
  border-color: rgba(239, 68, 68, 0.2);
}

.match-result-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  font-size: 0.75rem;
  font-weight: 800;
  flex-shrink: 0;
}

.match-result-badge.W {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.match-result-badge.L {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.match-result-badge.\? {
  background: rgba(156, 163, 175, 0.15);
  color: #9ca3af;
}

.match-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.match-opponent {
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--color-text-primary);
}

.match-score {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  font-family: var(--font-mono, monospace);
}

.match-elo {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--color-brand-live, #22c55e);
  white-space: nowrap;
}

.match-date {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  white-space: nowrap;
}

/* Recent Matches List */
.recent-matches-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.recent-match {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-secondary);
  transition: background var(--transition-fast);
}

.recent-match:nth-child(even) {
  background: var(--color-surface);
}

.recent-match:hover {
  background: var(--color-bg-hover);
}

.recent-opponent {
  flex: 1;
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--color-text-primary);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-score {
  font-size: 0.8rem;
  font-family: var(--font-mono, monospace);
  color: var(--color-text-secondary);
  min-width: 60px;
  text-align: center;
}

.recent-elo {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--color-brand-live, #22c55e);
  min-width: 40px;
  text-align: right;
}

.recent-date {
  font-size: 0.72rem;
  color: var(--color-text-muted);
  min-width: 80px;
  text-align: right;
}

@media (max-width: 768px) {
  .player-modal {
    max-width: 100%;
    margin: var(--space-4);
    max-height: 90vh;
  }

  .detail-stats-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }

  .highlight-match {
    flex-wrap: wrap;
  }
}
</style>
