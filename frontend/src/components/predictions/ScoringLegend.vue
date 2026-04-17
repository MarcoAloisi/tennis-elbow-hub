<!-- frontend/src/components/predictions/ScoringLegend.vue -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DrawData } from '@/stores/predictions'

const props = defineProps<{
    draw: DrawData | null | undefined
}>()

const expanded = ref(false)

const ROUND_LABELS: Record<string, string> = {
    Q1: 'Q1', Q2: 'Q2', Q3: 'Q3', Q4: 'Q4', Q5: 'Q5', Q6: 'Q6', Qualified: 'Qualified',
    R1: 'Round 1', R2: 'Round 2', R3: 'Round 3', R4: 'Round 4',
    QF: 'Quarterfinal', SF: 'Semifinal', F: 'Final',
}

const ROUND_POINTS: Record<string, [number, number, number]> = {
    Q1: [2, 5, 4], Q2: [3, 8, 6], Q3: [3, 8, 6],
    Q4: [4, 10, 7], Q5: [4, 10, 7], Q6: [5, 12, 9], Qualified: [5, 12, 9],
    R1: [5, 15, 10], R2: [10, 25, 18], R3: [15, 35, 25], R4: [18, 40, 30],
    QF: [20, 50, 35], SF: [30, 75, 50], F: [50, 100, 70],
}

const ORDER = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Qualified',
    'R1', 'R2', 'R3', 'R4', 'QF', 'SF', 'F']

const rounds = computed(() => {
    const present = new Set(
        (props.draw?.matches ?? []).map(m => m.round)
    )
    const filtered = ORDER.filter(r => present.has(r))
    return filtered.length ? filtered : ORDER
})
</script>

<template>
    <div class="scoring-legend">
        <button class="legend-header" @click="expanded = !expanded">
            <span class="legend-title">
                <span class="legend-icon">⭐</span>
                How scoring works
            </span>
            <span class="legend-toggle">{{ expanded ? '▾' : '▸' }}</span>
        </button>

        <div v-if="expanded" class="legend-body">
            <p class="rules">
                For each match, pick the <strong>winner</strong>, then optionally how many
                <strong>sets</strong> the match will go (2 / 3 / 4 / 5) or whether it ends in a
                <strong>retirement</strong>. Three tiers of points per round:
            </p>
            <ul class="rules-list">
                <li><strong>Tier 1</strong> — correct winner only.</li>
                <li><strong>Tier 2</strong> — correct winner + correct sets count.</li>
                <li><strong>Tier 3</strong> — correct winner + correctly predicted retirement (or walkover).</li>
            </ul>
            <table class="pts-table">
                <thead>
                    <tr>
                        <th>Round</th>
                        <th>Winner</th>
                        <th>+ Sets</th>
                        <th>+ Retired</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="r in rounds" :key="r">
                        <td class="round-cell">{{ ROUND_LABELS[r] ?? r }}</td>
                        <td>{{ ROUND_POINTS[r]?.[0] ?? '—' }}</td>
                        <td>{{ ROUND_POINTS[r]?.[1] ?? '—' }}</td>
                        <td>{{ ROUND_POINTS[r]?.[2] ?? '—' }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<style scoped>
.scoring-legend {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    margin-bottom: var(--space-4);
    overflow: hidden;
}
.legend-header {
    width: 100%; display: flex; align-items: center; justify-content: space-between;
    background: transparent; border: none; padding: var(--space-3) var(--space-4);
    cursor: pointer; color: var(--color-text-primary); font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
}
.legend-header:hover { background: var(--color-bg-hover); }
.legend-icon { margin-right: var(--space-2); }
.legend-toggle { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.legend-body {
    padding: var(--space-3) var(--space-4) var(--space-4);
    border-top: 1px solid var(--color-border);
    font-size: var(--font-size-sm); color: var(--color-text-secondary);
}
.rules { margin-bottom: var(--space-2); line-height: 1.5; }
.rules-list { margin: 0 0 var(--space-3) var(--space-4); padding: 0; line-height: 1.6; }
.rules-list li { margin-bottom: 2px; }
.pts-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-xs); font-family: var(--font-mono); }
.pts-table th {
    text-align: left; padding: var(--space-1) var(--space-2);
    border-bottom: 1px solid var(--color-border);
    color: var(--color-text-muted); font-weight: var(--font-weight-semibold);
    text-transform: uppercase; letter-spacing: 0.5px;
}
.pts-table td {
    padding: var(--space-1) var(--space-2);
    border-bottom: 1px solid var(--color-border);
    color: var(--color-text-primary);
}
.round-cell { color: var(--color-text-secondary); font-family: var(--font-sans); font-weight: var(--font-weight-medium); }
</style>
