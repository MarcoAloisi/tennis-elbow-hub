<!-- frontend/src/components/predictions/BracketEditor.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import type { DrawData, DrawMatch, PickData } from '@/stores/predictions'
import BracketMatch from './BracketMatch.vue'

const props = defineProps<{
    drawData: DrawData
    picks: Record<string, PickData>
    readonly: boolean
    section: 'main' | 'qualifying'
}>()

const emit = defineEmits<{
    pick: [matchId: string, patch: Partial<PickData>]
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

    // Both players known from backend → use directly
    if (match.player1.name !== 'TBD' && match.player2.name !== 'TBD') return match

    // At least one slot is TBD: fill from user picks in previous round
    const prevRound = rounds.value[roundIndex - 1]
    const prevMatches = matchesByRound.value[prevRound] ?? []
    const matchIdx = parseInt(match.id.split('_').pop() ?? '0', 10)
    const prev1 = prevMatches[matchIdx * 2]
    const prev2 = prevMatches[matchIdx * 2 + 1]
    const pick1 = prev1 ? (props.picks[prev1.id]?.winner ?? null) : null
    const pick2 = prev2 ? (props.picks[prev2.id]?.winner ?? null) : null

    return {
        ...match,
        player1: match.player1.name !== 'TBD'
            ? match.player1
            : pick1 ? { name: pick1, seed: null, player_id: null } : { name: 'TBD', seed: null, player_id: null },
        player2: match.player2.name !== 'TBD'
            ? match.player2
            : pick2 ? { name: pick2, seed: null, player_id: null } : { name: 'TBD', seed: null, player_id: null },
    }
}

const ROUND_LABELS: Record<string, string> = {
    R1: 'R1', R2: 'R2', R3: 'R3', R4: 'R4', QF: 'QF', SF: 'SF', F: 'F',
    Q1: 'Q1', Q2: 'Q2', Q3: 'Q3', Q4: 'Q4', Q5: 'Q5', Q6: 'Q6', Qualified: 'Q',
}

const ROUND_PTS: Record<string, string> = {
    R1: '5 / 15 / 20', R2: '10 / 25 / 35', R3: '15 / 35 / 50', R4: '18 / 40 / 58',
    QF: '20 / 50 / 70', SF: '30 / 75 / 105', F: '50 / 100 / 140',
    Q1: '2 / 5 / 7', Q2: '3 / 8 / 11', Q3: '3 / 8 / 11',
    Q4: '4 / 10 / 14', Q5: '4 / 10 / 14', Q6: '5 / 12 / 17', Qualified: '5 / 12 / 17',
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
                <span v-if="!readonly" class="round-pts" title="winner / +sets / +retirement">{{ ROUND_PTS[round] }} pts</span>
            </div>
            <div class="round-matches">
                <div
                    v-for="(match, matchIndex) in matchesByRound[round]"
                    :key="match.id"
                    class="match-wrapper"
                >
                    <!-- Left entry arm (not first round) -->
                    <div v-if="roundIndex > 0" class="conn-arm-left" />

                    <BracketMatch
                        :match="effectiveMatch(match, roundIndex)"
                        :picked-winner="picks[match.id]?.winner ?? null"
                        :picked-sets="picks[match.id]?.sets_count ?? null"
                        :picked-retirement="picks[match.id]?.retirement ?? false"
                        :readonly="readonly"
                        @pick="(id, patch) => emit('pick', id, patch)"
                    />

                    <!-- Right exit arm + vertical connector (not last round) -->
                    <template v-if="roundIndex < rounds.length - 1">
                        <div class="conn-arm-right" />
                        <div
                            class="conn-vert"
                            :class="matchIndex % 2 === 0 ? 'conn-vert-down' : 'conn-vert-up'"
                        />
                    </template>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.bracket-editor {
    display: flex;
    gap: 24px;
    overflow-x: auto;
    align-items: stretch;
    padding-bottom: var(--space-3);
}

.round-col {
    display: flex;
    flex-direction: column;
    min-width: 175px;
    flex-shrink: 0;
}

.round-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-2);
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

/* Each match wrapper fills an equal vertical slice of the column.
   flex: 1 ensures R1 slots are small, R2 slots are 2× taller, etc.
   Connectors are absolutely positioned and extend into the 24px gap. */
.match-wrapper {
    position: relative;
    display: flex;
    align-items: center;
    flex: 1;
    padding: 6px 0;
}

/* ── Connectors ─────────────────────────────────────────────────────── */
/* The 24px gap is split: right arm = 12px out, left arm = 12px in.
   Vertical connector sits at right edge + 12px (center of gap). */

.conn-arm-left {
    position: absolute;
    left: -12px;
    top: 50%;
    width: 12px;
    height: 1px;
    background: var(--color-border);
}

.conn-arm-right {
    position: absolute;
    right: -12px;
    top: 50%;
    width: 12px;
    height: 1px;
    background: var(--color-border);
}

.conn-vert {
    position: absolute;
    right: -12px;
    width: 1px;
    background: var(--color-border);
}

/* Top of pair: vertical from match center (50%) down to bottom of wrapper (100%) */
.conn-vert-down {
    top: 50%;
    height: 50%;
}

/* Bottom of pair: vertical from top of wrapper (0%) up to match center (50%) */
.conn-vert-up {
    top: 0;
    height: 50%;
}
</style>
