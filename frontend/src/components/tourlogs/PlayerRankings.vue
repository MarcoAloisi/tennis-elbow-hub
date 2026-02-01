<script setup>
/**
 * Player Rankings Component
 * Shows player win% and ELO rankings
 */
const props = defineProps({
    rankings: {
        type: Array,
        required: true
    }
})

// Get medal for top 3
function getMedal(index) {
    if (index === 0) return '🥇'
    if (index === 1) return '🥈'
    if (index === 2) return '🥉'
    return ''
}

// Get win% color class
function getWinPctClass(winPct) {
    const pct = parseFloat(winPct)
    if (pct >= 70) return 'win-excellent'
    if (pct >= 50) return 'win-good'
    if (pct >= 30) return 'win-average'
    return 'win-low'
}
</script>

<template>
    <div class="rankings-container">
        <div class="rankings-grid">
            <!-- Win% Rankings -->
            <div class="ranking-card">
                <h3 class="card-title">🏆 Win Rate Leaders</h3>
                <div class="ranking-list">
                    <div v-for="(player, index) in rankings.slice(0, 15)" 
                         :key="player.name"
                         class="ranking-item">
                        <span class="rank">
                            {{ getMedal(index) || `#${index + 1}` }}
                        </span>
                        <span class="player-name">{{ player.name }}</span>
                        <span class="player-stats">
                            <span :class="['win-pct', getWinPctClass(player.winPct)]">
                                {{ player.winPct }}%
                            </span>
                            <span class="record">{{ player.wins }}W - {{ player.losses }}L</span>
                        </span>
                    </div>
                    <div v-if="rankings.length === 0" class="empty-message">
                        No player data available
                    </div>
                </div>
            </div>
            
            <!-- ELO Rankings -->
            <div class="ranking-card">
                <h3 class="card-title">📊 ELO Rankings</h3>
                <div class="ranking-list">
                    <div v-for="(player, index) in [...rankings].filter(p => p.elo).sort((a, b) => b.elo - a.elo).slice(0, 15)" 
                         :key="player.name"
                         class="ranking-item">
                        <span class="rank">
                            {{ getMedal(index) || `#${index + 1}` }}
                        </span>
                        <span class="player-name">{{ player.name }}</span>
                        <span class="player-stats">
                            <span class="elo">{{ player.elo }}</span>
                            <span class="matches">{{ player.matches }} matches</span>
                        </span>
                    </div>
                </div>
            </div>
            
            <!-- Most Active -->
            <div class="ranking-card">
                <h3 class="card-title">⚡ Most Active</h3>
                <div class="ranking-list">
                    <div v-for="(player, index) in [...rankings].sort((a, b) => b.matches - a.matches).slice(0, 15)" 
                         :key="player.name"
                         class="ranking-item">
                        <span class="rank">
                            {{ getMedal(index) || `#${index + 1}` }}
                        </span>
                        <span class="player-name">{{ player.name }}</span>
                        <span class="player-stats">
                            <span class="matches-count">{{ player.matches }} matches</span>
                            <span class="record">{{ player.wins }}W - {{ player.losses }}L</span>
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.rankings-container {
    padding: var(--space-4) 0;
}

.rankings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: var(--space-6);
}

.ranking-card {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-border);
    overflow: hidden;
}

.card-title {
    padding: var(--space-4);
    margin: 0;
    background: var(--color-bg-secondary);
    border-bottom: 1px solid var(--color-border);
    font-size: 1rem;
    color: var(--color-text-primary);
}

.ranking-list {
    max-height: 500px;
    overflow-y: auto;
}

.ranking-item {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--color-border);
    transition: background var(--transition-fast);
}

.ranking-item:hover {
    background: var(--color-bg-hover, rgba(0, 0, 0, 0.02));
}

.ranking-item:last-child {
    border-bottom: none;
}

.rank {
    min-width: 35px;
    font-weight: 600;
    color: var(--color-text-secondary);
}

.player-name {
    flex: 1;
    font-weight: 500;
    color: var(--color-text-primary);
}

.player-stats {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
}

.win-pct {
    font-weight: 700;
    font-size: 0.95rem;
}

.win-excellent {
    color: #22c55e;
}

.win-good {
    color: #84cc16;
}

.win-average {
    color: #f59e0b;
}

.win-low {
    color: #ef4444;
}

.record, .matches {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
}

.elo {
    font-weight: 700;
    color: var(--color-brand-primary);
}

.matches-count {
    font-weight: 600;
    color: var(--color-brand-primary);
}

.empty-message {
    padding: var(--space-6);
    text-align: center;
    color: var(--color-text-secondary);
}
</style>
