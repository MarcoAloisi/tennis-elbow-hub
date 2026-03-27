<script setup lang="ts">
import { ref } from 'vue'
import { useAdminPlayers } from '@/composables/useAdminPlayers'
import { useNicknameMapping } from '@/composables/useNicknameMapping'
import type { SortField } from '@/composables/useAdminPlayers'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { Search, ArrowUpDown, ArrowUp, ArrowDown, Database, X, Plus, Trash2, ChevronDown, ChevronUp, Check, Pencil } from 'lucide-vue-next'

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
const newCanonical = ref('')
const newAliasInput = ref('')
const newAliasTags = ref<string[]>([])

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
}
</style>
