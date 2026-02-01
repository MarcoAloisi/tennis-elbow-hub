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
    { key: 'player', label: 'Winner', width: '120px' },
    { key: 'elo', label: 'ELO', width: '70px' },
    { key: 'result', label: 'Result', width: '120px' },
    { key: 'opponent', label: 'Loser', width: '120px' },
    { key: 'opponentElo', label: 'Opp ELO', width: '70px' },
    { key: 'tournament', label: 'Tournament', width: '150px' },
    // Winner serve stats
    { key: 'firstServePct', label: 'W 1st%', width: '70px', format: 'pct' },
    { key: 'oppFirstServePct', label: 'L 1st%', width: '70px', format: 'pct' },
    { key: 'aces', label: 'W Aces', width: '65px' },
    { key: 'oppAces', label: 'L Aces', width: '65px' },
    { key: 'doubleFaults', label: 'W DF', width: '55px' },
    { key: 'oppDoubleFaults', label: 'L DF', width: '55px' },
    // Points
    { key: 'winners', label: 'W Wnrs', width: '65px' },
    { key: 'oppWinners', label: 'L Wnrs', width: '65px' },
    { key: 'unforcedErrors', label: 'W UE', width: '55px' },
    { key: 'oppUnforcedErrors', label: 'L UE', width: '55px' },
    // Serve won
    { key: 'firstServeWonPct', label: 'W 1stW%', width: '75px', format: 'pct' },
    { key: 'oppFirstServeWonPct', label: 'L 1stW%', width: '75px', format: 'pct' },
    { key: 'secondServeWonPct', label: 'W 2ndW%', width: '75px', format: 'pct' },
    { key: 'oppSecondServeWonPct', label: 'L 2ndW%', width: '75px', format: 'pct' },
    // Return
    { key: 'returnPointsWonPct', label: 'W Ret%', width: '70px', format: 'pct' },
    { key: 'oppReturnPointsWonPct', label: 'L Ret%', width: '70px', format: 'pct' },
    { key: 'breakPointsWonPct', label: 'W BP%', width: '65px', format: 'pct' },
    { key: 'oppBreakPointsWonPct', label: 'L BP%', width: '65px', format: 'pct' },
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
                                'winner-cell': col.key === 'player',
                                'loser-cell': col.key === 'opponent',
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
            <span class="row-count">{{ data.length }} matches</span>
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

.winner-cell {
    color: var(--color-brand-primary);
    font-weight: 600;
}

.loser-cell {
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
