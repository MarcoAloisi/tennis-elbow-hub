<script setup>
/**
 * Tour Logs Data Table Component
 * Displays filterable match statistics table
 */
import { computed } from 'vue'

const props = defineProps({
    data: {
        type: Array,
        required: true
    }
})

// Table columns configuration
const columns = [
    { key: 'date', label: 'Date', width: '100px' },
    { key: 'player', label: 'Player', width: '120px' },
    { key: 'elo', label: 'ELO', width: '70px' },
    { key: 'result', label: 'Result', width: '120px' },
    { key: 'opponent', label: 'Opponent', width: '120px' },
    { key: 'opponentElo', label: 'Opp ELO', width: '70px' },
    { key: 'tournament', label: 'Tournament', width: '150px' },
    // Player stats (Opponent stats removed as they appear in their own row)
    { key: 'firstServePct', label: '1st%', width: '70px', format: 'pct' },
    { key: 'aces', label: 'Aces', width: '65px' },
    { key: 'doubleFaults', label: 'DF', width: '55px' },
    // Points
    { key: 'winners', label: 'Wnrs', width: '65px' },
    { key: 'unforcedErrors', label: 'UE', width: '55px' },
    // Serve won
    { key: 'firstServeWonPct', label: '1stW%', width: '75px', format: 'pct' },
    { key: 'secondServeWonPct', label: '2ndW%', width: '75px', format: 'pct' },
    // Return
    { key: 'returnPointsWonPct', label: 'Ret%', width: '70px', format: 'pct' },
    { key: 'breakPointsWonPct', label: 'BP%', width: '65px', format: 'pct' },
]

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
</script>

<template>
    <div class="table-container">
        <div class="table-scroll">
            <table class="data-table">
                <thead>
                    <tr>
                        <th v-for="col in columns" :key="col.key" :style="{ minWidth: col.width }">
                            {{ col.label }}
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, index) in data" :key="index">
                        <td v-for="col in columns" :key="col.key" 
                            :class="{
                                'player-cell': col.key === 'player',
                                'opponent-cell': col.key === 'opponent',
                                [getEloDiffClass(row.elo, row.opponentElo)]: col.key === 'elo'
                            }">
                            {{ formatValue(row[col.key], col.format) }}
                        </td>
                    </tr>
                    <tr v-if="data.length === 0">
                        <td :colspan="columns.length" class="empty-row">
                            No matches found
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="table-footer">
            <span class="row-count">{{ data.length }} records</span>
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
    font-size: 0.875rem;
}

.data-table th {
    position: sticky;
    top: 0;
    background: var(--color-bg-secondary);
    padding: var(--space-3) var(--space-2);
    text-align: left;
    font-weight: 600;
    color: var(--color-text-primary);
    border-bottom: 2px solid var(--color-border);
    white-space: nowrap;
    z-index: 1;
}

.data-table td {
    padding: var(--space-2);
    border-bottom: 1px solid var(--color-border);
    color: var(--color-text-secondary);
    white-space: nowrap;
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
    padding: var(--space-3) var(--space-4);
    background: var(--color-bg-secondary);
    border-top: 1px solid var(--color-border);
}

.row-count {
    font-size: 0.875rem;
    color: var(--color-text-secondary);
}
</style>
