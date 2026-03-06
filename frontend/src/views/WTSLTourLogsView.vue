<script setup lang="ts">
/**
 * WTSL Tour Logs View
 * Main view for tour logs with subtabs, filters, and data display
 */
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useTourLogsStore } from '@/stores/tourLogs'
import TourLogsTable from '@/components/tourlogs/TourLogsTable.vue'
import StatsLeaders from '@/components/tourlogs/StatsLeaders.vue'
import PlayerStatsGrid from '@/components/tourlogs/PlayerStatsGrid.vue'
import { Table, Medal, ChartColumn, TriangleAlert } from 'lucide-vue-next'

const store = useTourLogsStore()
const showPlayerDropdown = ref(false)
const playerInput = ref('')
let debounceTimer = null

// Fetch data on mount
onMounted(() => {
    if (store.data.length === 0) {
        store.fetchData()
    }
})

// Subtab configuration
const tabs = [
    { id: 'data', label: 'Match Data', icon: Table },
    { id: 'leaders', label: 'Stats Leaders', icon: Medal },
    { id: 'playerstats', label: 'Player Stats', icon: ChartColumn },
]

// Debounced player filter update
function onPlayerInput(event) {
    const value = event.target.value
    playerInput.value = value
    showPlayerDropdown.value = true
    
    // Debounce the store update
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
        store.setPlayerFilter(value)
    }, 300)
}

// Select player from suggestion
function handleSelectPlayer(player) {
    playerInput.value = player
    store.selectPlayer(player)
    showPlayerDropdown.value = false
}

// Handle input focus/blur
function onPlayerInputFocus() {
    showPlayerDropdown.value = true
}

function onPlayerInputBlur() {
    // Delay to allow click on suggestion
    setTimeout(() => {
        showPlayerDropdown.value = false
    }, 200)
}
</script>

<template>
    <div class="tour-logs-view">
        <!-- Breadcrumb -->
        <RouterLink to="/online-tours/wtsl" class="breadcrumb">
            ← Back to WTSL Tour
        </RouterLink>

        <!-- Header -->
        <div class="page-header">
            <div class="header-content">
                <h1>WTSL Tour Logs</h1>
                <p>Explore match statistics and leaderboards</p>
            </div>
        </div>

        <!-- Loading State -->
        <div v-if="store.isLoading" class="loading-container">
            <div class="loading-spinner"></div>
            <p>Loading tour logs data...</p>
        </div>

        <!-- Error State -->
        <div v-else-if="store.error" class="error-container">
            <span class="error-icon"><TriangleAlert :size="32" class="error-icon-color" /></span>
            <p>{{ store.error }}</p>
            <button @click="store.fetchData()" class="btn btn-primary">Retry</button>
        </div>

        <!-- Content -->
        <div v-else class="content-container">
            <!-- Filters Bar -->
            <div class="filters-bar">
                <!-- Player search with autocomplete -->
                <div class="filter-group player-filter">
                    <label class="filter-label">Search Player</label>
                    <div class="autocomplete-container">
                        <input 
                            type="text" 
                            :value="playerInput" 
                            placeholder="Type player name..."
                            class="filter-input"
                            @input="onPlayerInput"
                            @focus="onPlayerInputFocus"
                            @blur="onPlayerInputBlur"
                        />
                        <div v-if="showPlayerDropdown && store.playerSuggestions.length > 0" class="autocomplete-dropdown">
                            <div 
                                v-for="player in store.playerSuggestions" 
                                :key="player"
                                class="autocomplete-item"
                                @mousedown="handleSelectPlayer(player)"
                            >
                                {{ player }}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tournament filter with normalized names -->
                <div class="filter-group">
                    <label class="filter-label">Tournament</label>
                    <select v-model="store.filters.tournament" class="filter-select">
                        <option value="">All Tournaments</option>
                        <option v-for="t in store.uniqueTournaments" :key="(t as string)" :value="t">
                            {{ t }}
                        </option>
                    </select>
                </div>

                <!-- Date range -->
                <div class="filter-group">
                    <label class="filter-label">Date Range</label>
                    <div class="date-range">
                        <input type="date" v-model="store.filters.dateStart" class="filter-input date-input" />
                        <span class="date-separator">to</span>
                        <input type="date" v-model="store.filters.dateEnd" class="filter-input date-input" />
                    </div>
                </div>

                <button @click="store.resetFilters()" class="btn btn-ghost">
                    Reset Filters
                </button>
            </div>

            <!-- Subtab Navigation -->
            <div class="subtab-nav">
                <button 
                    v-for="tab in tabs" 
                    :key="tab.id"
                    :class="['subtab-btn', 'tab-' + tab.id, { active: store.activeTab === tab.id }]"
                    @click="store.activeTab = tab.id"
                >
                    <span class="tab-icon-wrapper"><component :is="tab.icon" :size="16" stroke-width="2.5" /></span>
                    <span class="tab-label">{{ tab.label }}</span>
                </button>
            </div>

            <!-- Tab Content -->
            <div class="tab-content">
                <!-- Match Data Tab -->
                <TourLogsTable 
                    v-if="store.activeTab === 'data'" 
                    :data="store.filteredData" 
                />

                <!-- Stats Leaders Tab -->
                <StatsLeaders 
                    v-if="store.activeTab === 'leaders'" 
                    :leaders="store.statsLeaders"
                />

                <!-- Player Stats Tab -->
                <PlayerStatsGrid 
                    v-if="store.activeTab === 'playerstats'" 
                    :stats="store.currentPlayerStats"
                />
            </div>

            <!-- Last Updated Footer -->
            <div v-if="store.latestMatchDate" class="tour-logs-footer">
                <span class="last-updated">Last match recorded: {{ store.latestMatchDate }}</span>
            </div>
        </div>
    </div>
</template>

<style scoped>
.tour-logs-view {
    min-height: calc(100vh - 200px);
}

.breadcrumb {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    margin-bottom: var(--space-4);
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-md);
    transition: all var(--transition-fast);
}

.breadcrumb:hover {
    color: var(--color-text-primary);
    background: var(--color-bg-hover);
}

.page-header {
    margin-bottom: var(--space-6);
}

.page-header h1 {
    margin: 0 0 var(--space-2);
    color: var(--color-text-primary);
}

.page-header p {
    margin: 0;
    color: var(--color-text-secondary);
}

/* Loading & Error */
.loading-container,
.error-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-16);
    text-align: center;
    color: var(--color-text-secondary);
}

.loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-brand-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: var(--space-4);
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.error-icon {
    margin-bottom: var(--space-4);
}

.error-icon-color {
    color: var(--color-error);
}

/* Filters */
.filters-bar {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-4);
    align-items: flex-end;
    padding: var(--space-4);
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-border);
    margin-bottom: var(--space-6);
}

.filter-group {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
}

.filter-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.filter-input,
.filter-select {
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg-primary);
    color: var(--color-text-primary);
    font-size: 0.875rem;
    min-width: 150px;
}

.filter-input:focus,
.filter-select:focus {
    outline: none;
    border-color: var(--color-brand-primary);
}

.date-range {
    display: flex;
    align-items: center;
    gap: var(--space-2);
}

.date-separator {
    color: var(--color-text-secondary);
    font-size: 0.875rem;
}

.date-input {
    min-width: 130px;
}

/* Player Autocomplete */
.player-filter {
    position: relative;
}

.autocomplete-container {
    position: relative;
}

.autocomplete-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    max-height: 200px;
    overflow-y: auto;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-top: none;
    border-radius: 0 0 var(--radius-md) var(--radius-md);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    z-index: 100;
}

.autocomplete-item {
    padding: var(--space-2) var(--space-3);
    cursor: pointer;
    color: var(--color-text-primary);
    font-size: 0.875rem;
}

.autocomplete-item:hover {
    background: var(--color-bg-hover);
}

/* Subtabs */
.subtab-nav {
    display: flex;
    gap: var(--space-2);
    margin-bottom: var(--space-6);
    border-bottom: 2px solid var(--color-border);
    padding-bottom: var(--space-2);
}

.subtab-btn {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border: none;
    background: transparent;
    color: var(--color-text-secondary);
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    border-radius: var(--radius-md) var(--radius-md) 0 0;
    transition: all var(--transition-fast);
}

.subtab-btn:hover {
    color: var(--color-text-primary);
    background: var(--color-bg-hover);
}

.subtab-btn.active {
    color: var(--color-brand-primary);
    background: var(--color-accent-light);
    border-bottom: 2px solid var(--color-brand-primary);
    margin-bottom: -2px;
}

.tab-icon-wrapper {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 6px;
    transition: all var(--transition-fast);
}

.tab-data .tab-icon-wrapper { color: #60a5fa; }
.tab-leaders .tab-icon-wrapper { color: #f59e0b; }
.tab-playerstats .tab-icon-wrapper { color: #a855f7; }

.subtab-btn.active .tab-icon-wrapper {
    color: currentColor; 
}

/* Buttons */
.btn {
    padding: var(--space-2) var(--space-4);
    border-radius: var(--radius-md);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all var(--transition-fast);
    border: none;
}

.btn-primary {
    background: var(--color-brand-primary);
    color: var(--color-text-inverse);
}

.btn-primary:hover {
    opacity: 0.9;
}

.btn-ghost {
    background: transparent;
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
}

.btn-ghost:hover {
    background: var(--color-bg-hover);
    color: var(--color-text-primary);
}

/* Footer */
.tour-logs-footer {
    margin-top: var(--space-6);
    padding-top: var(--space-4);
    border-top: 1px solid var(--color-border);
    text-align: right;
}

.last-updated {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    font-style: italic;
}

/* Responsive */
@media (max-width: 768px) {
    .filters-bar {
        flex-direction: column;
        align-items: stretch;
    }

    .filter-input,
    .filter-select {
        width: 100%;
    }

    .subtab-nav {
        overflow-x: auto;
    }

    .subtab-btn {
        white-space: nowrap;
    }
}
</style>
