<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAdminPlayers } from '@/composables/useAdminPlayers'
import { useNicknameMapping } from '@/composables/useNicknameMapping'
import { usePlayerDetails } from '@/composables/usePlayerDetails'
import { useModalAccessibility } from '@/composables/useModalAccessibility'
import type { SortField } from '@/composables/useAdminPlayers'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { Search, ArrowUpDown, ArrowUp, ArrowDown, Database, X, Plus, Trash2, ChevronDown, ChevronUp, Check, Pencil, Filter, TrendingUp, TrendingDown, BarChart3, Hash, Trophy, Target, Calendar, Activity } from 'lucide-vue-next'

const {
  players,
  allPlayers,
  isLoading,
  error,
  lastRefreshed,
  searchQuery,
  sortField,
  sortDirection,
  eloMin,
  eloMax,
  matchesMin,
  matchesMax,
  highestElo,
  highestEloPlayer,
  lowestElo,
  lowestEloPlayer,
  avgElo,
  avgMatchesPlayed,
  fetchPlayers,
  downloadCsv,
  openInGoogleSheets,
  setSort,
  clearError,
  clearFilters,
} = useAdminPlayers()

const {
  groupedAliases,
  isLoading: aliasLoading,
  isSaving,
  error: aliasError,
  successMessage,
  saveAliases,
  deleteAlias,
  renameCanonical,
  clearError: clearAliasError,
  clearSuccess,
  fetchAliases,
} = useNicknameMapping()

// Panel UI state
const showMapper = ref(false)
const showFilters = ref(false)
const showPlayerModal = ref(false)
const newCanonical = ref('')
const newAliasInput = ref('')
const newAliasTags = ref<string[]>([])

// Player detail modal
const {
  details: playerDetails,
  isLoading: playerDetailsLoading,
  error: playerDetailsError,
  fetchPlayerDetails,
  clearDetails,
} = usePlayerDetails()

useModalAccessibility(showPlayerModal, {
  onClose: () => closePlayerModal()
})

function openPlayerModal(playerName: string) {
  showPlayerModal.value = true
  fetchPlayerDetails(playerName)
}

function closePlayerModal() {
  showPlayerModal.value = false
  clearDetails()
}

function toggleMapper() {
  showMapper.value = !showMapper.value
}

function addAliasTag() {
  const tag = newAliasInput.value.trim()
  if (tag && !newAliasTags.value.includes(tag.toLowerCase())) {
    newAliasTags.value.push(tag)
    newAliasInput.value = ''
  }
}

function removeAliasTag(index: number) {
  newAliasTags.value.splice(index, 1)
}

function handleAliasKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    addAliasTag()
  }
}

async function handleSave() {
  if (!newCanonical.value.trim() || newAliasTags.value.length === 0) return
  await saveAliases(newCanonical.value.trim(), newAliasTags.value)
  // After a successful save, also refresh the player table so it reflects the new aliases
  newCanonical.value = ''
  newAliasTags.value = []
  newAliasInput.value = ''
  fetchPlayers()
}

async function handleDelete(alias: string) {
  await deleteAlias(alias)
  fetchPlayers()
}

// Rename state
const renamingGroup = ref<string | null>(null)
const renameInput = ref('')

function startRename(canonicalName: string) {
  renamingGroup.value = canonicalName
  renameInput.value = canonicalName
}

function cancelRename() {
  renamingGroup.value = null
  renameInput.value = ''
}

async function submitRename(oldName: string) {
  const newName = renameInput.value.trim()
  if (!newName || newName === oldName) {
    cancelRename()
    return
  }
  await renameCanonical(oldName, newName)
  renamingGroup.value = null
  renameInput.value = ''
  fetchPlayers()
}

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

function parseFilterInput(value: string): number | null {
  if (!value || value.trim() === '') return null
  const num = Number(value)
  return isNaN(num) ? null : num
}

const hasActiveFilters = computed(() =>
  eloMin.value !== null || eloMax.value !== null ||
  matchesMin.value !== null || matchesMax.value !== null
)
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
        <button class="btn-toolbar btn-filter" @click="showFilters = !showFilters" :class="{ active: showFilters || hasActiveFilters }" title="Filter players">
          <Filter :size="14" class="btn-icon" />
          <span>Filters</span>
          <span v-if="hasActiveFilters" class="filter-badge">●</span>
        </button>
        <button class="btn-toolbar btn-mapper" @click="toggleMapper" :class="{ active: showMapper }" title="Nickname Mapper">
          <span>Nickname Mapper</span>
          <component :is="showMapper ? ChevronUp : ChevronDown" :size="14" class="btn-chevron" />
        </button>
        <button class="btn-toolbar" @click="fetchPlayers" :disabled="isLoading" title="Refresh data">
          <span>Refresh</span>
        </button>
        <button class="btn-toolbar" @click="downloadCsv" :disabled="isLoading || !allPlayers.length" title="Download CSV">
          <span>Download CSV</span>
        </button>
        <button class="btn-toolbar btn-sheets" @click="openInGoogleSheets" :disabled="isLoading || !allPlayers.length" title="Open in Google Sheets">
          <span>Google Sheets</span>
        </button>
      </div>
    </div>

    <!-- ─── Nickname Mapper Panel ─── -->
    <Transition name="panel-slide">
      <div v-if="showMapper" class="mapper-panel">
        <div class="mapper-header">
          <div class="mapper-title">
            <Users :size="20" />
            <h2>Nickname Mapper</h2>
          </div>
          <p class="mapper-desc">Map alternate nicknames to a single original player name. Enter the original name, then type each alias and press <strong>Enter</strong> to add it as a tag. Click <strong>Save Mapping</strong> when done — stats will be consolidated automatically.</p>
        </div>

        <!-- Alias error / success -->
        <ErrorAlert v-if="aliasError" :message="aliasError" type="error" @dismiss="clearAliasError" />
        <div v-if="successMessage" class="success-alert">
          <Check :size="16" />
          <span>{{ successMessage }}</span>
          <button class="dismiss-btn" @click="clearSuccess"><X :size="14" /></button>
        </div>

        <!-- Create form -->
        <div class="mapper-form">
          <div class="form-row">
            <div class="form-field">
              <label for="canonical-name">Original Name</label>
              <input
                id="canonical-name"
                v-model="newCanonical"
                type="text"
                placeholder="e.g. barboza"
                class="mapper-input"
                list="player-suggestions"
              />
              <datalist id="player-suggestions">
                <option v-for="p in allPlayers" :key="p.name" :value="p.name" />
              </datalist>
            </div>
            <div class="form-field form-field-grow">
              <label for="alias-input">Aliases</label>
              <div class="tags-input-wrapper">
                <div class="tags-list" v-if="newAliasTags.length">
                  <span class="alias-tag" v-for="(tag, i) in newAliasTags" :key="tag">
                    {{ tag }}
                    <button class="tag-remove" @click="removeAliasTag(i)"><X :size="12" /></button>
                  </span>
                </div>
                <input
                  id="alias-input"
                  v-model="newAliasInput"
                  type="text"
                  placeholder="Type alias, press Enter..."
                  class="mapper-input tags-input"
                  list="alias-suggestions"
                  @keydown="handleAliasKeydown"
                />
                <datalist id="alias-suggestions">
                  <option v-for="p in allPlayers" :key="p.name" :value="p.name" />
                </datalist>
              </div>
            </div>
          </div>
          <button
            class="btn-save"
            @click="handleSave"
            :disabled="isSaving || !newCanonical.trim() || newAliasTags.length === 0"
          >
            <Plus :size="16" v-if="!isSaving" />
            <LoadingSpinner v-else size="sm" />
            <span>Save Mapping</span>
          </button>
        </div>

        <!-- Existing mappings -->
        <div class="mappings-section" v-if="groupedAliases.length">
          <h3>Active Mappings</h3>
          <div class="mappings-grid">
            <div class="mapping-card" v-for="group in groupedAliases" :key="group.canonical_name">
              <div class="mapping-header">
                <template v-if="renamingGroup === group.canonical_name">
                  <input
                    v-model="renameInput"
                    class="rename-input"
                    @keydown.enter="submitRename(group.canonical_name)"
                    @keydown.escape="cancelRename"
                    list="player-suggestions"
                  />
                  <button class="rename-action-btn save" @click="submitRename(group.canonical_name)" title="Confirm rename">
                    <Check :size="14" />
                  </button>
                  <button class="rename-action-btn cancel" @click="cancelRename" title="Cancel">
                    <X :size="14" />
                  </button>
                </template>
                <template v-else>
                  <div class="mapping-canonical">{{ group.canonical_name }}</div>
                  <button class="rename-btn" @click="startRename(group.canonical_name)" title="Rename player">
                    <Pencil :size="13" />
                  </button>
                </template>
              </div>
              <div class="mapping-aliases">
                <span class="mapping-alias" v-for="alias in group.aliases" :key="alias">
                  {{ alias }}
                  <button class="alias-delete" @click="handleDelete(alias)" title="Remove alias">
                    <Trash2 :size="12" />
                  </button>
                </span>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="!aliasLoading" class="mappings-empty">
          <p>No nickname mappings yet. Create one above.</p>
        </div>
      </div>
    </Transition>

    <!-- KPI Cards -->
    <div class="kpi-grid" v-if="allPlayers.length">
      <div class="kpi-card kpi-highest" @click="highestEloPlayer && openPlayerModal(highestEloPlayer)" :class="{ clickable: !!highestEloPlayer }">
        <div class="kpi-icon-wrap">
          <TrendingUp :size="20" />
        </div>
        <div class="kpi-content">
          <span class="kpi-label">Highest ELO</span>
          <span class="kpi-value">{{ highestElo ?? '—' }}</span>
          <span class="kpi-player" v-if="highestEloPlayer">{{ highestEloPlayer }}</span>
        </div>
      </div>
      <div class="kpi-card kpi-lowest" @click="lowestEloPlayer && openPlayerModal(lowestEloPlayer)" :class="{ clickable: !!lowestEloPlayer }">
        <div class="kpi-icon-wrap">
          <TrendingDown :size="20" />
        </div>
        <div class="kpi-content">
          <span class="kpi-label">Lowest ELO</span>
          <span class="kpi-value">{{ lowestElo ?? '—' }}</span>
          <span class="kpi-player" v-if="lowestEloPlayer">{{ lowestEloPlayer }}</span>
        </div>
      </div>
      <div class="kpi-card kpi-avg-elo">
        <div class="kpi-icon-wrap">
          <BarChart3 :size="20" />
        </div>
        <div class="kpi-content">
          <span class="kpi-label">AVG ELO</span>
          <span class="kpi-value">{{ avgElo ?? '—' }}</span>
        </div>
      </div>
      <div class="kpi-card kpi-avg-matches">
        <div class="kpi-icon-wrap">
          <Hash :size="20" />
        </div>
        <div class="kpi-content">
          <span class="kpi-label">AVG Matches</span>
          <span class="kpi-value">{{ avgMatchesPlayed ?? '—' }}</span>
        </div>
      </div>
    </div>

    <!-- Filters Panel -->
    <Transition name="panel-slide">
      <div v-if="showFilters" class="filters-panel">
        <div class="filters-grid">
          <div class="filter-group">
            <label class="filter-label">ELO Range</label>
            <div class="filter-inputs">
              <input
                type="number"
                placeholder="Min"
                class="filter-input"
                :value="eloMin"
                @input="eloMin = parseFilterInput(($event.target as HTMLInputElement).value)"
              />
              <span class="filter-sep">—</span>
              <input
                type="number"
                placeholder="Max"
                class="filter-input"
                :value="eloMax"
                @input="eloMax = parseFilterInput(($event.target as HTMLInputElement).value)"
              />
            </div>
          </div>
          <div class="filter-group">
            <label class="filter-label">Matches Played</label>
            <div class="filter-inputs">
              <input
                type="number"
                placeholder="Min"
                class="filter-input"
                :value="matchesMin"
                @input="matchesMin = parseFilterInput(($event.target as HTMLInputElement).value)"
              />
              <span class="filter-sep">—</span>
              <input
                type="number"
                placeholder="Max"
                class="filter-input"
                :value="matchesMax"
                @input="matchesMax = parseFilterInput(($event.target as HTMLInputElement).value)"
              />
            </div>
          </div>
          <div class="filter-actions">
            <button class="btn-clear-filters" @click="clearFilters" :disabled="!hasActiveFilters">
              <X :size="14" />
              <span>Clear Filters</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Stats bar -->
    <div class="stats-bar" v-if="allPlayers.length">
      <span class="stat-pill">
        <strong>{{ allPlayers.length }}</strong> total players
      </span>
      <span class="stat-pill" v-if="searchQuery || hasActiveFilters">
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
              <td class="col-name player-cell player-clickable" @click="openPlayerModal(player.name)">{{ player.name }}</td>
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

    <!-- Player Detail Modal -->
    <div v-if="showPlayerModal" class="modal-overlay" @click.self="closePlayerModal" role="dialog" aria-modal="true" aria-label="Player details">
      <div class="player-modal">
        <div class="player-modal-header">
          <h2 v-if="playerDetails">{{ playerDetails.name }}</h2>
          <h2 v-else>Loading…</h2>
          <button class="modal-close" @click="closePlayerModal" aria-label="Close">
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

        <div v-else-if="playerDetails" class="player-modal-body">
          <!-- Stats Grid -->
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

          <!-- Activity -->
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

          <!-- Best Win -->
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

          <!-- Worst Loss -->
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

          <!-- Recent Matches -->
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

.btn-mapper {
  color: #a78bfa;
  border-color: rgba(167, 139, 250, 0.3);
}

.btn-mapper:hover:not(:disabled) {
  background: rgba(167, 139, 250, 0.08);
  color: #a78bfa;
  border-color: rgba(167, 139, 250, 0.5);
}

.btn-mapper.active {
  background: rgba(167, 139, 250, 0.12);
  color: #a78bfa;
  border-color: rgba(167, 139, 250, 0.5);
}

.btn-chevron {
  opacity: 0.6;
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

/* ─── Nickname Mapper Panel ─── */
.mapper-panel {
  background: var(--color-surface);
  border: 1px solid rgba(167, 139, 250, 0.25);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  margin-bottom: var(--space-6);
  box-shadow: 0 0 24px rgba(167, 139, 250, 0.06);
}

.mapper-header {
  margin-bottom: var(--space-5);
}

.mapper-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: #a78bfa;
  margin-bottom: var(--space-2);
}

.mapper-title h2 {
  font-size: 1.2rem;
  font-weight: 700;
  margin: 0;
}

.mapper-desc {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin: 0;
}

.success-alert {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 10px 14px;
  background: rgba(52, 168, 83, 0.1);
  border: 1px solid rgba(52, 168, 83, 0.3);
  border-radius: var(--radius-md);
  color: #34a853;
  font-size: var(--font-size-sm);
  margin-bottom: var(--space-4);
}

.dismiss-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 2px;
  opacity: 0.6;
  transition: opacity var(--transition-fast);
}

.dismiss-btn:hover {
  opacity: 1;
}

/* Form */
.mapper-form {
  margin-bottom: var(--space-5);
}

.form-row {
  display: flex;
  gap: var(--space-4);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 200px;
}

.form-field-grow {
  flex: 1;
}

.form-field label {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-secondary);
}

.mapper-input {
  padding: 10px 14px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-family: inherit;
  transition: all var(--transition-fast);
}

.mapper-input:focus {
  outline: none;
  border-color: #a78bfa;
  box-shadow: 0 0 0 2px rgba(167, 139, 250, 0.15);
}

.mapper-input::placeholder {
  color: var(--color-text-muted);
}

.tags-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.alias-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(167, 139, 250, 0.12);
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: var(--radius-full);
  color: #c4b5fd;
  font-size: 0.8rem;
  font-weight: 600;
}

.tag-remove {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0;
  opacity: 0.6;
  display: flex;
  align-items: center;
  transition: opacity var(--transition-fast);
}

.tag-remove:hover {
  opacity: 1;
}

.btn-save {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 10px 20px;
  background: rgba(167, 139, 250, 0.15);
  border: 1px solid rgba(167, 139, 250, 0.4);
  border-radius: var(--radius-md);
  color: #a78bfa;
  font-size: var(--font-size-sm);
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-save:hover:not(:disabled) {
  background: rgba(167, 139, 250, 0.25);
  border-color: rgba(167, 139, 250, 0.6);
}

.btn-save:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Existing mappings */
.mappings-section h3 {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-3);
  font-weight: 700;
}

.mappings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-3);
}

.mapping-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  transition: border-color var(--transition-fast);
}

.mapping-card:hover {
  border-color: rgba(167, 139, 250, 0.3);
}

.mapping-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.mapping-canonical {
  font-weight: 700;
  font-size: 1rem;
  color: var(--color-text-primary);
}

.rename-btn {
  background: none;
  border: none;
  color: var(--color-brand-primary);
  cursor: pointer;
  padding: 2px;
  opacity: 0.5;
  display: flex;
  align-items: center;
  transition: all var(--transition-fast);
}

.rename-btn:hover {
  opacity: 1;
}

.rename-input {
  flex: 1;
  padding: 4px 8px;
  background: var(--color-bg-secondary);
  border: 1px solid #a78bfa;
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  font-size: 0.95rem;
  font-weight: 600;
  font-family: inherit;
  outline: none;
  box-shadow: 0 0 0 2px rgba(167, 139, 250, 0.15);
}

.rename-action-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.rename-action-btn.save {
  color: #34a853;
}

.rename-action-btn.save:hover {
  background: rgba(52, 168, 83, 0.12);
}

.rename-action-btn.cancel {
  color: var(--color-text-muted);
}

.rename-action-btn.cancel:hover {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.mapping-aliases {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.mapping-alias {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
  font-size: 0.78rem;
  font-weight: 500;
  transition: all var(--transition-fast);
}

.mapping-alias:hover {
  border-color: rgba(239, 68, 68, 0.4);
}

.alias-delete {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  padding: 0;
  opacity: 0;
  display: flex;
  align-items: center;
  transition: opacity var(--transition-fast);
}

.mapping-alias:hover .alias-delete {
  opacity: 0.7;
}

.alias-delete:hover {
  opacity: 1 !important;
}

.mappings-empty {
  text-align: center;
  padding: var(--space-4);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

/* Panel transition */
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
  margin-bottom: 0;
}

.panel-slide-enter-to,
.panel-slide-leave-from {
  opacity: 1;
  max-height: 800px;
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

/* ─── KPI Cards ─── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-5);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.kpi-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.kpi-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.kpi-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
  color: var(--color-text-muted);
}

.kpi-value {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.1;
  color: var(--color-text-primary);
}

/* KPI color variants */
.kpi-highest .kpi-icon-wrap {
  background: rgba(34, 197, 94, 0.12);
  color: #22c55e;
}

.kpi-lowest .kpi-icon-wrap {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.kpi-avg-elo .kpi-icon-wrap {
  background: rgba(59, 130, 246, 0.12);
  color: #3b82f6;
}

.kpi-avg-matches .kpi-icon-wrap {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}

[data-theme="dark"] .kpi-highest .kpi-icon-wrap { color: #4ade80; }
[data-theme="dark"] .kpi-lowest .kpi-icon-wrap { color: #f87171; }
[data-theme="dark"] .kpi-avg-elo .kpi-icon-wrap { color: #60a5fa; }
[data-theme="dark"] .kpi-avg-matches .kpi-icon-wrap { color: #fbbf24; }

/* ─── Filters Panel ─── */
.filters-panel {
  background: var(--color-surface);
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  margin-bottom: var(--space-5);
  box-shadow: 0 0 24px rgba(59, 130, 246, 0.06);
}

.filters-grid {
  display: flex;
  align-items: flex-end;
  gap: var(--space-6);
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.filter-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
  color: var(--color-text-secondary);
}

.filter-inputs {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.filter-input {
  width: 100px;
  padding: 8px 12px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-family: inherit;
  transition: all var(--transition-fast);
}

.filter-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.filter-input::placeholder {
  color: var(--color-text-muted);
}

/* Remove number input spinners */
.filter-input::-webkit-outer-spin-button,
.filter-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.filter-input[type=number] {
  -moz-appearance: textfield;
}

.filter-sep {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.filter-actions {
  display: flex;
  align-items: flex-end;
}

.btn-clear-filters {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 8px 14px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: var(--radius-md);
  color: #ef4444;
  font-size: var(--font-size-sm);
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-clear-filters:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.4);
}

.btn-clear-filters:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Filter button styles */
.btn-filter {
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.3);
}

.btn-filter:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.08);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.5);
}

.btn-filter.active {
  background: rgba(59, 130, 246, 0.12);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.5);
}

.filter-badge {
  font-size: 0.6rem;
  color: #3b82f6;
  margin-left: -2px;
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

  .form-row {
    flex-direction: column;
  }

  .mappings-grid {
    grid-template-columns: 1fr;
  }

  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-3);
  }

  .kpi-value {
    font-size: 1.2rem;
  }

  .filters-grid {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-input {
    flex: 1;
    width: auto;
  }

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

/* ─── KPI Player Name ─── */
.kpi-player {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-card.clickable {
  cursor: pointer;
}

.kpi-card.clickable:hover .kpi-player {
  color: var(--color-accent);
  text-decoration: underline;
}

/* ─── Clickable Player Names ─── */
.player-clickable {
  cursor: pointer;
  transition: color var(--transition-fast);
}

.player-clickable:hover {
  color: var(--color-accent) !important;
  text-decoration: underline;
}

/* ─── Player Detail Modal ─── */
.modal-overlay {
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
</style>
