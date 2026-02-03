<script setup>
/**
 * Tour Logs Data Table Component
 * Displays filterable match statistics table with sortable columns
 */
import { ref, computed } from 'vue'

const props = defineProps({
    data: {
        type: Array,
        required: true
    }
})

// Sorting state
const sortKey = ref('date')
const sortOrder = ref('desc') // 'asc' or 'desc'

// Table columns configuration - ALL columns from original data
const columns = [
    // Match info
    { key: 'date', label: 'Date', width: '95px' },
    { key: 'player', label: 'Player', width: '120px' },
    { key: 'elo', label: 'ELO', width: '60px' },
    { key: 'result', label: 'Result', width: '90px' },
    { key: 'opponent', label: 'Opponent', width: '120px' },
    { key: 'opponentElo', label: 'Opp ELO', width: '70px' },
    { key: 'tournament', label: 'Tournament', width: '140px' },
    // Serve stats
    { key: 'firstServePct', label: '1st%', width: '60px', format: 'pct' },
    { key: 'aces', label: 'Aces', width: '50px' },
    { key: 'doubleFaults', label: 'DF', width: '45px' },
    { key: 'fastestServe', label: 'Fast', width: '55px' },
    { key: 'avgFirstServeSpeed', label: '1stSpd', width: '60px', format: 'decimal' },
    { key: 'avgSecondServeSpeed', label: '2ndSpd', width: '60px', format: 'decimal' },
    { key: 'firstServeWonPct', label: '1stW%', width: '60px', format: 'pct' },
    { key: 'secondServeWonPct', label: '2ndW%', width: '65px', format: 'pct' },
    // Points
    { key: 'winners', label: 'Wnrs', width: '55px' },
    { key: 'forcedErrors', label: 'FE', width: '45px' },
    { key: 'unforcedErrors', label: 'UE', width: '45px' },
    { key: 'totalPointsWon', label: 'Pts', width: '50px' },
    // Return
    { key: 'returnPointsWonPct', label: 'Ret%', width: '55px', format: 'pct' },
    { key: 'returnWinners', label: 'RetW', width: '55px' },
    // Break points
    { key: 'breakPointsWonPct', label: 'BP%', width: '55px', format: 'pct' },
    { key: 'breaksPerGamePct', label: 'Brk%', width: '55px', format: 'pct' },
    // Saves
    { key: 'setPointsSaved', label: 'SPS', width: '50px' },
    { key: 'matchPointsSaved', label: 'MPS', width: '50px' },
    // Net
    { key: 'netPointsWonPct', label: 'Net%', width: '55px', format: 'pct' },
    // Rallies
    { key: 'shortRalliesWonPct', label: 'Short%', width: '60px', format: 'pct' },
    { key: 'mediumRalliesWonPct', label: 'Med%', width: '55px', format: 'pct' },
    { key: 'longRalliesWonPct', label: 'Long%', width: '60px', format: 'pct' },
    { key: 'avgRallyLength', label: 'AvgRal', width: '60px', format: 'decimal' },
]

// Sorted data
const sortedData = computed(() => {
    if (!props.data || props.data.length === 0) return []
    
    return [...props.data].sort((a, b) => {
        let aVal = a[sortKey.value]
        let bVal = b[sortKey.value]
        
        // Handle null/undefined
        if (aVal == null && bVal == null) return 0
        if (aVal == null) return sortOrder.value === 'asc' ? 1 : -1
        if (bVal == null) return sortOrder.value === 'asc' ? -1 : 1
        
        // Handle dates (DD/MM/YYYY format)
        if (sortKey.value === 'date') {
            const parseDate = (str) => {
                if (!str) return new Date(0)
                const [d, m, y] = str.split('/')
                return new Date(y, m - 1, d)
            }
            aVal = parseDate(aVal)
            bVal = parseDate(bVal)
        }
        
        // Handle strings
        if (typeof aVal === 'string' && typeof bVal === 'string') {
            const cmp = aVal.localeCompare(bVal, undefined, { sensitivity: 'base' })
            return sortOrder.value === 'asc' ? cmp : -cmp
        }
        
        // Handle numbers
        if (sortOrder.value === 'asc') {
            return aVal < bVal ? -1 : aVal > bVal ? 1 : 0
        } else {
            return aVal > bVal ? -1 : aVal < bVal ? 1 : 0
        }
    })
})

// Toggle sort on column click
function toggleSort(key) {
    if (sortKey.value === key) {
        sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
        sortKey.value = key
        sortOrder.value = 'desc'
    }
}

// Format cell value
function formatValue(value, format) {
    if (value === null || value === undefined) return '-'
    if (format === 'pct') return `${value.toFixed(0)}%`
    if (format === 'decimal') return value.toFixed(1)
    return value
}

// Get ELO difference class
function getEloDiffClass(playerElo, opponentElo) {
    if (!playerElo || !opponentElo) return ''
    const diff = playerElo - opponentElo
    if (diff > 200) return 'elo-higher'
    if (diff < -200) return 'elo-lower'
    return ''
}

// Get sort indicator
function getSortIndicator(key) {
    if (sortKey.value !== key) return ''
    return sortOrder.value === 'asc' ? '↑' : '↓'
}
</script>

<template>
    <div class="table-container">
        <div class="table-scroll">
            <table class="data-table">
                <thead>
                    <tr>
                        <th 
                            v-for="col in columns" 
                            :key="col.key" 
                            :style="{ minWidth: col.width }"
                            :class="{ 'sortable': true, 'sorted': sortKey === col.key }"
                            @click="toggleSort(col.key)"
                        >
                            <span class="th-content">
                                {{ col.label }}
                                <span class="sort-indicator">{{ getSortIndicator(col.key) }}</span>
                            </span>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, index) in sortedData" :key="index">
                        <td v-for="col in columns" :key="col.key" 
                            :class="{
                                'player-cell': col.key === 'player',
                                'opponent-cell': col.key === 'opponent',
                                [getEloDiffClass(row.elo, row.opponentElo)]: col.key === 'elo'
                            }">
                            {{ formatValue(row[col.key], col.format) }}
                        </td>
                    </tr>
                    <tr v-if="sortedData.length === 0">
                        <td :colspan="columns.length" class="empty-row">
                            No matches found
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="table-footer">
            <span class="row-count">{{ sortedData.length }} records</span>
            <span class="sort-info" v-if="sortKey">
                Sorted by: {{ columns.find(c => c.key === sortKey)?.label }} 
                ({{ sortOrder === 'asc' ? 'ascending' : 'descending' }})
            </span>
        </div>
    </div>
</template>

<style scoped>
.table-container {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--color-border);
}

.table-scroll {
    overflow-x: auto;
    max-height: 600px;
    overflow-y: auto;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
}

.data-table th {
    position: sticky;
    top: 0;
    background: var(--color-bg-secondary);
    padding: var(--space-2) var(--space-1);
    text-align: left;
    font-weight: 600;
    color: var(--color-text-primary);
    border-bottom: 2px solid var(--color-border);
    white-space: nowrap;
    z-index: 1;
}

.data-table th.sortable {
    cursor: pointer;
    user-select: none;
    transition: background var(--transition-fast);
}

.data-table th.sortable:hover {
    background: var(--color-bg-hover);
}

.data-table th.sorted {
    background: var(--color-accent-light);
    color: var(--color-brand-primary);
}

.th-content {
    display: flex;
    align-items: center;
    gap: var(--space-1);
}

.sort-indicator {
    font-size: 0.7rem;
    opacity: 0.8;
    min-width: 10px;
}

.data-table td {
    padding: var(--space-1) var(--space-1);
    border-bottom: 1px solid var(--color-border);
    color: var(--color-text-secondary);
    white-space: nowrap;
    font-size: 0.75rem;
}

.data-table tbody tr:hover {
    background: var(--color-bg-hover, rgba(0, 0, 0, 0.02));
}

.player-cell {
    color: var(--color-brand-primary);
    font-weight: 600;
}

.opponent-cell {
    color: var(--color-text-secondary);
}

.elo-higher {
    color: #22c55e;
    font-weight: 600;
}

.elo-lower {
    color: #ef4444;
}

.empty-row {
    text-align: center;
    padding: var(--space-8) !important;
    color: var(--color-text-secondary);
}

.table-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-3) var(--space-4);
    background: var(--color-bg-secondary);
    border-top: 1px solid var(--color-border);
}

.row-count {
    font-size: 0.875rem;
    color: var(--color-text-secondary);
}

.sort-info {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    font-style: italic;
}
</style>
