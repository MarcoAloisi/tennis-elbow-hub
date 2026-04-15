<!-- frontend/src/components/predictions/BracketEditor.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import type { DrawData, DrawMatch } from '@/stores/predictions'
import BracketMatch from './BracketMatch.vue'

const props = defineProps<{
    drawData: DrawData
    picks: Record<string, { winner: string; score?: string }>
    readonly: boolean
    section: 'main' | 'qualifying'
}>()

const emit = defineEmits<{
    pick: [matchId: string, winner: string, score: string | undefined]
}>()

// Canonical round order — only rounds present in draw_data will be shown
const MAIN_ROUND_ORDER = ['R1', 'R2', 'R3', 'R4', 'QF', 'SF', 'F']
const QUAL_ROUND_ORDER = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Qualified']

const rounds = computed(() => {
    const order = props.section === 'main' ? MAIN_ROUND_ORDER : QUAL_ROUND_ORDER
    const present = new Set(
        props.drawData.matches
            .filter(m => m.section === props.section)
            .map(m => m.round)
    )
    return order.filter(r => present.has(r))
})

// Group matches by round, filtered to this section
const matchesByRound = computed(() => {
    const sectionMatches = props.drawData.matches.filter(m => m.section === props.section)
    const map: Record<string, DrawMatch[]> = {}
    for (const round of rounds.value) {
        map[round] = sectionMatches.filter(m => m.round === round)
    }
    return map
})

// For R2+ rounds: prefer actual backend player names when known (draw started),
// fall back to deriving from user picks for still-unplayed future slots.
function effectiveMatch(match: DrawMatch, roundIndex: number): DrawMatch {
    if (roundIndex === 0) return match

    // Backend has real names → use them directly
    if (match.player1.name !== 'TBD' || match.player2.name !== 'TBD') return match

    // Both TBD: derive from what the user picked in the previous round
    const prevRound = rounds.value[roundIndex - 1]
    const prevMatches = matchesByRound.value[prevRound] ?? []
    const matchIdx = parseInt(match.id.split('_').pop() ?? '0', 10)
    const prev1 = prevMatches[matchIdx * 2]
    const prev2 = prevMatches[matchIdx * 2 + 1]
    const pick1 = prev1 ? (props.picks[prev1.id]?.winner ?? null) : null
    const pick2 = prev2 ? (props.picks[prev2.id]?.winner ?? null) : null

    return {
        ...match,
        player1: pick1 ? { name: pick1, seed: null, player_id: null } : { name: 'TBD', seed: null, player_id: null },
        player2: pick2 ? { name: pick2, seed: null, player_id: null } : { name: 'TBD', seed: null, player_id: null },
    }
}

const ROUND_LABELS: Record<string, string> = {
    R1: 'R1', R2: 'R2', R3: 'R3', R4: 'R4', QF: 'QF', SF: 'SF', F: 'F',
    Q1: 'Q1', Q2: 'Q2', Q3: 'Q3', Q4: 'Q4', Q5: 'Q5', Q6: 'Q6', Qualified: 'Q',
}

const ROUND_PTS: Record<string, string> = {
    R1: '5/30', R2: '10/50', R3: '15/70', R4: '18/80', QF: '20/100', SF: '30/150', F: '50/200',
    Q1: '2/10', Q2: '3/15', Q3: '3/15', Q4: '4/20', Q5: '4/20', Q6: '5/25', Qualified: '5/25',
}
</script>

<template>
    <div class="bracket-editor">
        <div
            v-for="(round, roundIndex) in rounds"
            :key="round"
            class="round-col"
        >
            <div class="round-header">
                <span class="round-name">{{ ROUND_LABELS[round] }}</span>
                <span class="round-pts">{{ ROUND_PTS[round] }} pts</span>
            </div>
            <div class="round-matches">
                <div
                    v-for="(match, matchIndex) in matchesByRound[round]"
                    :key="match.id"
                    class="match-wrapper"
                    :style="{ '--depth': roundIndex }"
                >
                    <BracketMatch
                        :match="effectiveMatch(match, roundIndex)"
                        :picked-winner="picks[match.id]?.winner ?? null"
                        :picked-score="picks[match.id]?.score"
                        :readonly="readonly"
                        @pick="(id, w, s) => emit('pick', id, w, s)"
                    />
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.bracket-editor {
    display: flex;
    gap: 0;
    overflow-x: auto;
    padding-bottom: var(--space-3);
}
.round-col {
    display: flex;
    flex-direction: column;
    min-width: 170px;
    flex-shrink: 0;
}
.round-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-2) var(--space-2);
    border-bottom: 1px solid var(--color-border);
    margin-bottom: var(--space-2);
}
.round-name {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-bold);
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--color-text-secondary);
}
.round-pts {
    font-size: var(--font-size-xs);
    color: var(--color-accent);
    font-weight: var(--font-weight-semibold);
    font-family: var(--font-mono);
}
.round-matches {
    display: flex;
    flex-direction: column;
    flex: 1;
}
.match-wrapper {
    display: flex;
    align-items: center;
    padding: calc(var(--space-1) * (1 + var(--depth, 0))) var(--space-2);
    flex: 1;
}
</style>
