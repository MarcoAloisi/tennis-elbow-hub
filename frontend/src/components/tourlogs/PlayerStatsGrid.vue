<script setup>
/**
 * Player Stats Grid Component
 * Displays player statistics or tour averages in a grid format
 */
import { computed } from 'vue'

const props = defineProps({
    stats: {
        type: Object,
        default: null
    }
})

// Format number with 1 decimal place
function fmt(val, decimals = 1) {
    if (val === null || val === undefined) return '-'
    return Number(val).toFixed(decimals)
}

// Format percentage with proper display
function fmtPct(val) {
    if (val === null || val === undefined) return '-'
    return `${Number(val).toFixed(1)}%`
}

// Get color class for percentage values
function getPercentClass(value) {
    const num = parseFloat(value)
    if (isNaN(num)) return ''
    if (num <= 30) return 'pct-danger'
    if (num < 50) return 'pct-warning'
    if (num <= 60) return 'pct-neutral'
    if (num < 90) return 'pct-good'
    return 'pct-excellent'
}

// Header text based on whether it's tour average or player stats
const headerText = computed(() => {
    if (!props.stats) return ''
    if (props.stats.name === 'Tour Average') {
        return `Tour Average (${props.stats.playerCount} players)`
    }
    return props.stats.name
})

const matchCount = computed(() => {
    if (!props.stats) return 0
    return props.stats.matches || 0
})
</script>

<template>
    <div v-if="stats" class="player-stats-grid">
        <!-- Header -->
        <div class="stats-header">
            <h3 class="stats-title">{{ headerText }}</h3>
            <span class="match-count">{{ matchCount }} matches analyzed</span>
        </div>

        <!-- Key Stats Row (4 columns) -->
        <div class="stats-grid stats-grid-4">
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.winners) }}</div>
                <div class="stat-label">Avg Winners</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.unforcedErrors) }}</div>
                <div class="stat-label">Avg Errors</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.aces) }}</div>
                <div class="stat-label">Avg Aces</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.doubleFaults) }}</div>
                <div class="stat-label">Avg D.Faults</div>
            </div>
        </div>

        <!-- Detailed Stats Grid (5 columns) -->
        <div class="stats-grid stats-grid-5">
            <!-- Row 1: Serve Stats -->
            <div class="stat-item">
                <div class="stat-value" :class="getPercentClass(stats.firstServePct)">{{ fmtPct(stats.firstServePct) }}</div>
                <div class="stat-label">1st Serve %</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.aces) }}</div>
                <div class="stat-label">Aces</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.doubleFaults) }}</div>
                <div class="stat-label">Double Faults</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.avgFirstServeSpeed, 0) }} km/h</div>
                <div class="stat-label">Avg 1st Serve</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.avgSecondServeSpeed, 0) }} km/h</div>
                <div class="stat-label">Avg 2nd Serve</div>
            </div>

            <!-- Row 2: Serve Speed & Rally -->
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.fastestServe, 0) }} km/h</div>
                <div class="stat-label">Fastest Serve</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" :class="getPercentClass(stats.shortRalliesWonPct)">{{ fmtPct(stats.shortRalliesWonPct) }}</div>
                <div class="stat-label">Short Rallies (&lt;5)</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" :class="getPercentClass(stats.mediumRalliesWonPct)">{{ fmtPct(stats.mediumRalliesWonPct) }}</div>
                <div class="stat-label">Medium Rallies (5-8)</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" :class="getPercentClass(stats.longRalliesWonPct)">{{ fmtPct(stats.longRalliesWonPct) }}</div>
                <div class="stat-label">Long Rallies (&gt;8)</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.avgRallyLength) }}</div>
                <div class="stat-label">Avg Rally Length</div>
            </div>

            <!-- Row 3: Points & Errors -->
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.winners) }}</div>
                <div class="stat-label">Winners</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.forcedErrors) }}</div>
                <div class="stat-label">Forced Errors</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.unforcedErrors) }}</div>
                <div class="stat-label">Unforced Errors</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" :class="getPercentClass(stats.firstServeWonPct)">{{ fmtPct(stats.firstServeWonPct) }}</div>
                <div class="stat-label">1st Serve Won %</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" :class="getPercentClass(stats.secondServeWonPct)">{{ fmtPct(stats.secondServeWonPct) }}</div>
                <div class="stat-label">2nd Serve Won %</div>
            </div>

            <!-- Row 4: Return & Net -->
            <div class="stat-item">
                <div class="stat-value" :class="getPercentClass(stats.returnPointsWonPct)">{{ fmtPct(stats.returnPointsWonPct) }}</div>
                <div class="stat-label">Return Points Won</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.returnWinners) }}</div>
                <div class="stat-label">Return Winners</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" :class="getPercentClass(stats.netPointsWonPct)">{{ fmtPct(stats.netPointsWonPct) }}</div>
                <div class="stat-label">Net Points Won</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.totalPointsWon, 0) }}</div>
                <div class="stat-label">Total Points Won</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" :class="getPercentClass(stats.breakPointsWonPct)">{{ fmtPct(stats.breakPointsWonPct) }}</div>
                <div class="stat-label">Break Points Won</div>
            </div>

            <!-- Row 5: Break & Save -->
            <div class="stat-item">
                <div class="stat-value" :class="getPercentClass(stats.breaksPerGamePct)">{{ fmtPct(stats.breaksPerGamePct) }}</div>
                <div class="stat-label">Breaks / Games</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.setPointsSaved) }}</div>
                <div class="stat-label">Set Points Saved</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{{ fmt(stats.matchPointsSaved) }}</div>
                <div class="stat-label">Match Points Saved</div>
            </div>
            <div class="stat-item empty"></div>
            <div class="stat-item empty"></div>
        </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
        <div class="empty-icon">📊</div>
        <p>No statistics available</p>
        <span class="empty-hint">Upload tour log data to see player statistics</span>
    </div>
</template>

<style scoped>
.player-stats-grid {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
}

.stats-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--space-2);
}

.stats-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    margin: 0;
    color: var(--color-text-primary);
}

.match-count {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
}

/* Stats Grids */
.stats-grid {
    display: grid;
    gap: var(--space-3);
}

.stats-grid-4 {
    grid-template-columns: repeat(4, 1fr);
}

.stats-grid-5 {
    grid-template-columns: repeat(5, 1fr);
}

@media (max-width: 1024px) {
    .stats-grid-5 {
        grid-template-columns: repeat(4, 1fr);
    }
}

@media (max-width: 768px) {
    .stats-grid-4 {
        grid-template-columns: repeat(2, 1fr);
    }
    .stats-grid-5 {
        grid-template-columns: repeat(3, 1fr);
    }
}

@media (max-width: 480px) {
    .stats-grid-4,
    .stats-grid-5 {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* Stat Items */
.stat-item {
    text-align: center;
    padding: var(--space-4);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-md);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-item:hover:not(.empty) {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

[data-theme="dark"] .stat-item:hover:not(.empty) {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.stat-item.empty {
    background: transparent;
}

.stat-value {
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: var(--color-text-primary);
    line-height: 1.2;
}

.stat-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    margin-top: var(--space-1);
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

/* Percentage Colors */
.pct-danger { color: #dc2626 !important; }
.pct-warning { color: #f97316 !important; }
.pct-neutral { color: var(--color-text-primary) !important; }
.pct-good { color: #22c55e !important; }
.pct-excellent { color: var(--color-brand-primary) !important; }

[data-theme="dark"] .pct-excellent {
    color: #D4FF5F !important;
}

/* Empty State */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-10);
    text-align: center;
    color: var(--color-text-muted);
}

.empty-icon {
    font-size: 3rem;
    margin-bottom: var(--space-4);
    opacity: 0.5;
}

.empty-state p {
    font-size: var(--font-size-lg);
    margin: 0 0 var(--space-2);
}

.empty-hint {
    font-size: var(--font-size-sm);
}
</style>
