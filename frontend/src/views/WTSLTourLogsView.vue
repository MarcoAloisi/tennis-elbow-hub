<script setup>
/**
 * WTSL Tour Logs View
 * Main view for tour logs with subtabs, filters, and data display
 */
import { onMounted, ref, watch } from 'vue'
import { useTourLogsStore } from '@/stores/tourLogs'
import TourLogsTable from '@/components/tourlogs/TourLogsTable.vue'
import PlayerRankings from '@/components/tourlogs/PlayerRankings.vue'
import StatsLeaders from '@/components/tourlogs/StatsLeaders.vue'

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
    { id: 'data', label: 'Match Data', icon: '📋' },
    { id: 'rankings', label: 'Rankings', icon: '🏆' },
    { id: 'leaders', label: 'Stats Leaders', icon: '⭐' },
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
        <!-- Header -->
        <div class="page-header">
            <div class="header-content">
                <h1>WTSL Tour Logs</h1>
                <p>Explore match statistics, player rankings, and leaderboards</p>
            </div>
        </div>

        <!-- Loading State -->
        <div v-if="store.isLoading" class="loading-container">
            <div class="loading-spinner"></div>
            <p>Loading tour logs data...</p>
        </div>

        <!-- Error State -->
        <div v-else-if="store.error" class="error-container">
            <span class="error-icon">⚠️</span>
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
                        <option v-for="t in store.uniqueTournaments" :key="t" :value="t">
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
                    :class="['subtab-btn', { active: store.activeTab === tab.id }]"
                    @click="store.activeTab = tab.id"
                >
                    <span class="tab-icon">{{ tab.icon }}</span>
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

                <!-- Rankings Tab -->
                <PlayerRankings 
                    v-if="store.activeTab === 'rankings'" 
                    :rankings="store.playerRankings" 
                />

                <!-- Stats Leaders Tab -->
                <StatsLeaders 
                    v-if="store.activeTab === 'leaders'" 
                    :leaders="store.statsLeaders"
                />
            </div>
        </div>
    </div>
</template>

<style scoped>
.tour-logs-view {
    min-height: calc(100vh - 200px);
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
    font-size: 2rem;
    margin-bottom: var(--space-4);
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

/* Toggle */
.toggle-container {
    display: flex;
    align-items: center;
}

.toggle {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    cursor: pointer;
}

.toggle input {
    display: none;
}

.toggle-slider {
    width: 44px;
    height: 24px;
    background: var(--color-border);
    border-radius: 12px;
    position: relative;
    transition: background var(--transition-fast);
}

.toggle-slider::before {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    background: white;
    border-radius: 50%;
    transition: transform var(--transition-fast);
}

.toggle input:checked + .toggle-slider {
    background: var(--color-brand-primary);
}

.toggle input:checked + .toggle-slider::before {
    transform: translateX(20px);
}

.toggle-label {
    font-size: 0.875rem;
    color: var(--color-text-primary);
    font-weight: 500;
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

.tab-icon {
    font-size: 1.1rem;
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
