<script setup lang="ts">
import { useAdminPlayers } from '@/composables/useAdminPlayers'
import type { SortField } from '@/composables/useAdminPlayers'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { RefreshCw, Download, FileSpreadsheet, Search, ArrowUpDown, ArrowUp, ArrowDown, Database } from 'lucide-vue-next'

const {
  players,
  allPlayers,
  isLoading,
  error,
  lastRefreshed,
  searchQuery,
  sortField,
  sortDirection,
  fetchPlayers,
  downloadCsv,
  openInGoogleSheets,
  setSort,
  clearError,
} = useAdminPlayers()

function formatDate(isoString: string | null): string {
  if (!isoString) return '—'
  return new Date(isoString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

function formatRefreshed(isoString: string | null): string {
  if (!isoString) return ''
  return new Date(isoString).toLocaleString()
}

function getSortIcon(field: SortField) {
  if (sortField.value !== field) return ArrowUpDown
  return sortDirection.value === 'asc' ? ArrowUp : ArrowDown
}
</script>

<template>
  <div class="admin-players-view">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-title-row">
          <div class="header-icon-wrapper">
            <Database class="header-icon" :size="32" :stroke-width="1.5" />
          </div>
          <div>
            <h1>Players Database</h1>
            <p>All recorded players with ELO ratings and match history</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="search-wrapper">
        <Search class="search-icon" :size="18" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search players..."
          class="search-input"
          id="admin-player-search"
        />
      </div>

      <div class="toolbar-actions">
        <button class="btn-toolbar" @click="fetchPlayers" :disabled="isLoading" title="Refresh data">
          <RefreshCw class="btn-icon" :size="16" :class="{ spinning: isLoading }" />
          <span>Refresh</span>
        </button>
        <button class="btn-toolbar" @click="downloadCsv" :disabled="isLoading || !allPlayers.length" title="Download CSV">
          <Download class="btn-icon" :size="16" />
          <span>Download CSV</span>
        </button>
        <button class="btn-toolbar btn-sheets" @click="openInGoogleSheets" :disabled="isLoading || !allPlayers.length" title="Open in Google Sheets">
          <FileSpreadsheet class="btn-icon" :size="16" />
          <span>Google Sheets</span>
        </button>
      </div>
    </div>

    <!-- Stats bar -->
    <div class="stats-bar" v-if="allPlayers.length">
      <span class="stat-pill">
        <strong>{{ allPlayers.length }}</strong> total players
      </span>
      <span class="stat-pill" v-if="searchQuery">
        <strong>{{ players.length }}</strong> matching
      </span>
      <span class="stat-pill last-refresh" v-if="lastRefreshed">
        Last refreshed: {{ formatRefreshed(lastRefreshed) }}
      </span>
    </div>

    <!-- Error state -->
    <ErrorAlert
      v-if="error"
      :message="error"
      type="error"
      @dismiss="clearError"
    />

    <!-- Loading state -->
    <div v-if="isLoading && !allPlayers.length" class="loading-state">
      <LoadingSpinner size="lg" />
      <p>Loading players database...</p>
    </div>

    <!-- Table -->
    <div v-else-if="players.length > 0" class="table-card">
      <div class="table-wrapper">
        <table class="players-table">
          <thead>
            <tr>
              <th class="col-rank">#</th>
              <th class="col-name sortable" @click="setSort('name')">
                <span>Player</span>
                <component :is="getSortIcon('name')" :size="14" class="sort-icon" />
              </th>
              <th class="col-elo sortable text-right" @click="setSort('latest_elo')">
                <span>Latest ELO</span>
                <component :is="getSortIcon('latest_elo')" :size="14" class="sort-icon" />
              </th>
              <th class="col-matches sortable text-right" @click="setSort('total_matches')">
                <span>Matches</span>
                <component :is="getSortIcon('total_matches')" :size="14" class="sort-icon" />
              </th>
              <th class="col-date sortable text-right" @click="setSort('last_match_date')">
                <span>Last Match</span>
                <component :is="getSortIcon('last_match_date')" :size="14" class="sort-icon" />
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(player, index) in players" :key="player.name">
              <td class="col-rank rank-cell">{{ index + 1 }}</td>
              <td class="col-name player-cell">{{ player.name }}</td>
              <td class="col-elo text-right elo-cell">{{ player.latest_elo ?? '—' }}</td>
              <td class="col-matches text-right matches-cell">{{ player.total_matches }}</td>
              <td class="col-date text-right date-cell">{{ formatDate(player.last_match_date) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!isLoading" class="empty-state">
      <div class="empty-icon-wrapper">
        <Database class="empty-icon" :size="64" :stroke-width="1.5" />
      </div>
      <h3 v-if="searchQuery">No players match "{{ searchQuery }}"</h3>
      <h3 v-else>No player data yet</h3>
      <p>Player records will appear here once matches are tracked.</p>
    </div>
  </div>
</template>

<style scoped>
.admin-players-view {
  min-height: 100%;
}

.page-header {
  margin-bottom: var(--space-8);
  padding-top: var(--space-8);
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-5);
}

.header-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
  flex-shrink: 0;
}

[data-theme="dark"] .header-icon-wrapper {
  background: rgba(248, 113, 113, 0.12);
  color: #f87171;
}

.page-header h1 {
  margin-bottom: var(--space-1);
  font-size: 2.5rem;
  letter-spacing: -0.03em;
}

.page-header p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-md);
}

/* Toolbar */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}

.search-wrapper {
  position: relative;
  flex: 1;
  min-width: 220px;
  max-width: 400px;
}

.search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-muted);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 10px 14px 10px 42px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-family: inherit;
  transition: all var(--transition-fast);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 2px rgba(212, 255, 95, 0.15);
}

.search-input::placeholder {
  color: var(--color-text-muted);
}

.toolbar-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.btn-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 8px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all var(--transition-fast);
  min-height: 40px;
}

.btn-toolbar:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  border-color: var(--color-text-muted);
}

.btn-toolbar:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sheets {
  color: #34a853;
  border-color: rgba(52, 168, 83, 0.3);
}

.btn-sheets:hover:not(:disabled) {
  background: rgba(52, 168, 83, 0.08);
  color: #34a853;
  border-color: rgba(52, 168, 83, 0.5);
}

.btn-icon {
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinning {
  animation: spin 1s linear infinite;
}

/* Stats bar */
.stats-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}

.stat-pill {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  padding: 4px 12px;
  border-radius: var(--radius-full);
}

.stat-pill strong {
  color: var(--color-text-primary);
  font-weight: 700;
}

.last-refresh {
  margin-left: auto;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  background: transparent;
  border: none;
  padding: 0;
}

/* Table */
.table-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.players-table {
  width: 100%;
  border-collapse: collapse;
}

.players-table th,
.players-table td {
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  font-size: 0.9rem;
  white-space: nowrap;
}

.players-table th {
  text-align: left;
  font-weight: 700;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  text-transform: uppercase;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  position: sticky;
  top: 0;
  z-index: 1;
}

.players-table th.sortable {
  cursor: pointer;
  user-select: none;
  transition: color var(--transition-fast);
}

.players-table th.sortable:hover {
  color: var(--color-text-primary);
}

.sort-icon {
  display: inline-block;
  vertical-align: middle;
  margin-left: 4px;
  opacity: 0.5;
}

.players-table th.sortable:hover .sort-icon {
  opacity: 1;
}

.players-table tbody tr:last-child td {
  border-bottom: none;
}

.players-table tbody tr:hover {
  background: var(--color-bg-hover);
}

.text-right,
.players-table th.text-right {
  text-align: right;
}

.col-rank {
  width: 50px;
}

.rank-cell {
  color: var(--color-text-muted);
  font-weight: 600;
  font-size: 0.8rem;
}

.player-cell {
  font-weight: 600;
  color: var(--color-text-primary);
}

.elo-cell {
  font-weight: 700;
  color: var(--color-brand-live);
}

.matches-cell {
  font-weight: 700;
  color: var(--color-brand-primary);
}

.date-cell {
  color: var(--color-text-secondary);
  font-size: 0.85rem;
}

/* Loading state */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-16);
  gap: var(--space-4);
  color: var(--color-text-muted);
}

/* Empty state */
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
  max-width: 340px;
}

.empty-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  margin-bottom: var(--space-6);
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.15);
}

[data-theme="dark"] .empty-icon-wrapper {
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
  box-shadow: 0 0 20px rgba(248, 113, 113, 0.12);
}

/* Responsive */
@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-wrapper {
    max-width: none;
  }

  .toolbar-actions {
    justify-content: stretch;
  }

  .toolbar-actions .btn-toolbar {
    flex: 1;
    justify-content: center;
  }

  .page-header h1 {
    font-size: 1.8rem;
  }

  .header-icon-wrapper {
    width: 44px;
    height: 44px;
  }

  .stats-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .last-refresh {
    margin-left: 0;
  }

  .players-table th,
  .players-table td {
    padding: var(--space-2) var(--space-3);
    font-size: 0.8rem;
  }
}
</style>
