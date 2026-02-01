<script setup>
/**
 * Stats Leaders Component
 * Shows average stats per player for each stat category
 */
const props = defineProps({
    leaders: {
        type: Array,
        required: true
    }
})

// Stat categories for display
const statCategories = [
    {
        title: '🎾 Serve Stats',
        stats: [
            { key: 'firstServePct', label: '1st Serve %', format: 'pct', higher: true },
            { key: 'aces', label: 'Aces', format: 'decimal', higher: true },
            { key: 'doubleFaults', label: 'Double Faults', format: 'decimal', higher: false },
            { key: 'fastestServe', label: 'Fastest Serve', format: 'decimal', higher: true },
            { key: 'avgFirstServeSpeed', label: 'Avg 1st Speed', format: 'decimal', higher: true },
            { key: 'avgSecondServeSpeed', label: 'Avg 2nd Speed', format: 'decimal', higher: true },
        ]
    },
    {
        title: '🎯 Serve Won',
        stats: [
            { key: 'firstServeWonPct', label: '1st Serve Won %', format: 'pct', higher: true },
            { key: 'secondServeWonPct', label: '2nd Serve Won %', format: 'pct', higher: true },
        ]
    },
    {
        title: '💥 Points & Errors',
        stats: [
            { key: 'winners', label: 'Winners', format: 'decimal', higher: true },
            { key: 'forcedErrors', label: 'Forced Errors', format: 'decimal', higher: false },
            { key: 'unforcedErrors', label: 'Unforced Errors', format: 'decimal', higher: false },
            { key: 'totalPointsWon', label: 'Total Points Won', format: 'decimal', higher: true },
        ]
    },
    {
        title: '🌐 Net & Return',
        stats: [
            { key: 'netPointsWonPct', label: 'Net Points Won %', format: 'pct', higher: true },
            { key: 'returnPointsWonPct', label: 'Return Points Won %', format: 'pct', higher: true },
            { key: 'returnWinners', label: 'Return Winners', format: 'decimal', higher: true },
        ]
    },
    {
        title: '⚡ Break Points',
        stats: [
            { key: 'breakPointsWonPct', label: 'Break Points Won %', format: 'pct', higher: true },
            { key: 'breaksPerGamePct', label: 'Breaks / Games %', format: 'pct', higher: true },
            { key: 'setPointsSaved', label: 'Set Points Saved', format: 'decimal', higher: true },
            { key: 'matchPointsSaved', label: 'Match Points Saved', format: 'decimal', higher: true },
        ]
    },
    {
        title: '📊 Rally Stats',
        stats: [
            { key: 'shortRalliesWonPct', label: 'Short Rallies (<5)', format: 'pct', higher: true },
            { key: 'mediumRalliesWonPct', label: 'Medium Rallies (5-8)', format: 'pct', higher: true },
            { key: 'longRalliesWonPct', label: 'Long Rallies (>8)', format: 'pct', higher: true },
            { key: 'avgRallyLength', label: 'Shortest Rallies', format: 'decimal', higher: false },
            { key: 'avgRallyLength', label: 'Longest Rallies', format: 'decimal', higher: true },
        ]
    },
]

// Get top 5 players for a stat
function getTopPlayers(statKey, higher) {
    return [...props.leaders]
        .filter(p => p[statKey] !== null && p[statKey] !== undefined)
        .sort((a, b) => higher ? b[statKey] - a[statKey] : a[statKey] - b[statKey])
        .slice(0, 5)
}

// Format value
function formatValue(value, format) {
    if (value === null || value === undefined) return '-'
    if (format === 'pct') return `${value.toFixed(1)}%`
    return value.toFixed(1)
}

// Get medal
function getMedal(index) {
    if (index === 0) return '🥇'
    if (index === 1) return '🥈'
    if (index === 2) return '🥉'
    return `#${index + 1}`
}
</script>

<template>
    <div class="leaders-container">
        <div class="mode-indicator">
            Showing <strong>Average</strong> values per player
        </div>
        
        <div class="categories-grid">
            <div v-for="category in statCategories" :key="category.title" class="category-card">
                <h3 class="category-title">{{ category.title }}</h3>
                
                <div class="stats-list">
                    <div v-for="stat in category.stats" :key="stat.key" class="stat-section">
                        <div class="stat-header">
                            <span class="stat-name">{{ stat.label }}</span>
                            <span class="stat-direction">{{ stat.higher ? '↑ Better' : '↓ Better' }}</span>
                        </div>
                        
                        <div class="top-players">
                            <div v-for="(player, index) in getTopPlayers(stat.key, stat.higher)" 
                                 :key="player.name"
                                 class="player-row">
                                <span class="medal">{{ getMedal(index) }}</span>
                                <span class="name">{{ player.name }}</span>
                                <span class="value">{{ formatValue(player[stat.key], stat.format) }}</span>
                            </div>
                            <div v-if="getTopPlayers(stat.key, stat.higher).length === 0" class="no-data">
                                No data
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.leaders-container {
    padding: var(--space-4) 0;
}

.mode-indicator {
    background: var(--color-bg-secondary);
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-md);
    margin-bottom: var(--space-6);
    color: var(--color-text-secondary);
    font-size: 0.875rem;
}

.categories-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: var(--space-6);
}

.category-card {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-border);
    overflow: hidden;
}

.category-title {
    margin: 0;
    padding: var(--space-4);
    background: var(--color-bg-secondary);
    border-bottom: 1px solid var(--color-border);
    font-size: 1rem;
    color: var(--color-text-primary);
}

.stats-list {
    padding: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
}

.stat-section {
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-4);
}

.stat-section:last-child {
    border-bottom: none;
    padding-bottom: 0;
}

.stat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-2);
}

.stat-name {
    font-weight: 600;
    color: var(--color-text-primary);
    font-size: 0.9rem;
}

.stat-direction {
    font-size: 0.7rem;
    color: var(--color-text-secondary);
    background: var(--color-bg-tertiary);
    padding: 2px 6px;
    border-radius: 4px;
}

.top-players {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
}

.player-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-1) 0;
    font-size: 0.85rem;
}

.medal {
    min-width: 30px;
}

.name {
    flex: 1;
    color: var(--color-text-primary);
}

.value {
    font-weight: 600;
    color: var(--color-brand-primary);
    font-family: var(--font-data);
}

.no-data {
    color: var(--color-text-secondary);
    font-size: 0.8rem;
    font-style: italic;
}
</style>
