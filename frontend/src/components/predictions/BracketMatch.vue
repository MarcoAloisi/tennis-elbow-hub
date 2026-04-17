<!-- frontend/src/components/predictions/BracketMatch.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import type { DrawMatch, PickData, PlayerInfo, SetsCount } from '@/stores/predictions'

const props = defineProps<{
    match: DrawMatch
    pickedWinner: string | null
    pickedSets: number | null
    pickedRetirement: boolean
    readonly: boolean
}>()

const emit = defineEmits<{
    pick: [matchId: string, patch: Partial<PickData>]
}>()

function selectPlayer(player: PlayerInfo) {
    if (props.readonly || player.name === 'TBD') return
    emit('pick', props.match.id, { winner: player.name })
}

function selectSets(n: SetsCount) {
    if (props.readonly || !props.pickedWinner) return
    // Toggle off if same value clicked again
    const next = props.pickedSets === n ? undefined : n
    emit('pick', props.match.id, { sets_count: next, retirement: false })
}

function toggleRetirement() {
    if (props.readonly || !props.pickedWinner) return
    emit('pick', props.match.id, {
        retirement: !props.pickedRetirement,
        sets_count: undefined,
    })
}

function isSelected(player: PlayerInfo) {
    return props.pickedWinner === player.name
}
function isEliminated(player: PlayerInfo) {
    return props.pickedWinner !== null && props.pickedWinner !== player.name
}
function isActualWinner(player: PlayerInfo) {
    return props.match.winner === player.name
}
function isActualLoser(player: PlayerInfo) {
    return props.match.winner !== null && props.match.winner !== player.name
}

const ROUND_POINTS: Record<string, [number, number, number]> = {
    R1: [5, 15, 10], R2: [10, 25, 18], R3: [15, 35, 25], R4: [18, 40, 30],
    QF: [20, 50, 35], SF: [30, 75, 50], F: [50, 100, 70],
    Q1: [2, 5, 4], Q2: [3, 8, 6], Q3: [3, 8, 6],
    Q4: [4, 10, 7], Q5: [4, 10, 7], Q6: [5, 12, 9], Qualified: [5, 12, 9],
}
const tiers = computed(() => ROUND_POINTS[props.match.round] ?? [5, 15, 20])
const setsTooltip = computed(() => `Correct winner + correct sets = +${tiers.value[1]} pts`)
const retiredTooltip = computed(() => `Correct winner + correct retirement = +${tiers.value[2]} pts`)

function parseActualSets(score: string | null): { sets: number; retired: boolean } {
    if (!score) return { sets: 0, retired: false }
    const s = score.trim()
    const retired = /ret\.?$/i.test(s) || /^w\.?o\.?$/i.test(s)
    const cleaned = s.replace(/\s+ret\.?$/i, '').replace(/\(\d+\)/g, '').replace(/-/g, '/')
    let sets = 0
    for (const token of cleaned.split(/\s+/)) {
        const m = token.match(/^(\d+)\/(\d+)$/)
        if (m && Math.max(parseInt(m[1], 10), parseInt(m[2], 10)) >= 6) sets += 1
    }
    return { sets, retired }
}

const actualResult = computed(() => parseActualSets(props.match.score))
</script>

<template>
    <div class="bracket-match">
        <!-- Player 1 -->
        <div
            class="player-row"
            :class="{
                selected: isSelected(match.player1),
                eliminated: isEliminated(match.player1),
                'actual-winner': isActualWinner(match.player1),
                'actual-loser': isActualLoser(match.player1),
                tbd: match.player1.name === 'TBD',
                clickable: !readonly && match.player1.name !== 'TBD',
            }"
            @click="selectPlayer(match.player1)"
        >
            <span class="seed">{{ match.player1.seed ? `(${match.player1.seed})` : '' }}</span>
            <span class="name">{{ match.player1.name }}</span>
            <span v-if="isSelected(match.player1)" class="check">✓</span>
        </div>

        <div class="divider" />

        <!-- Player 2 -->
        <div
            class="player-row"
            :class="{
                selected: isSelected(match.player2),
                eliminated: isEliminated(match.player2),
                'actual-winner': isActualWinner(match.player2),
                'actual-loser': isActualLoser(match.player2),
                tbd: match.player2.name === 'TBD',
                clickable: !readonly && match.player2.name !== 'TBD',
            }"
            @click="selectPlayer(match.player2)"
        >
            <span class="seed">{{ match.player2.seed ? `(${match.player2.seed})` : '' }}</span>
            <span class="name">{{ match.player2.name }}</span>
            <span v-if="isSelected(match.player2)" class="check">✓</span>
        </div>

        <!-- Sets / Retirement picker -->
        <div v-if="!readonly && pickedWinner" class="pick-extras">
            <div class="extras-label" :title="setsTooltip">Sets</div>
            <div class="sets-row">
                <button
                    v-for="n in ([2, 3, 4, 5] as SetsCount[])"
                    :key="n"
                    class="sets-btn"
                    :class="{ active: pickedSets === n, disabled: pickedRetirement }"
                    :title="setsTooltip"
                    @click.stop="selectSets(n)"
                >{{ n }}</button>
                <button
                    class="sets-btn ret-btn"
                    :class="{ active: pickedRetirement }"
                    :title="retiredTooltip"
                    @click.stop="toggleRetirement"
                >Retired</button>
            </div>
        </div>

        <!-- Readonly: show actual result -->
        <div v-if="readonly && match.score" class="actual-score">
            <span class="actual-score-text">{{ match.score }}</span>
            <span v-if="actualResult.retired" class="actual-tag ret">retired</span>
            <span v-else-if="actualResult.sets > 0" class="actual-tag">{{ actualResult.sets }} sets</span>
        </div>
    </div>
</template>

<style scoped>
.bracket-match {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
    min-width: 150px;
    transition: border-color var(--transition-fast);
}
.bracket-match:hover { border-color: var(--color-border-hover); }
.player-row {
    display: flex; align-items: center; gap: var(--space-2);
    padding: 6px 10px; font-size: var(--font-size-sm); color: var(--color-text-secondary);
    transition: background var(--transition-fast), color var(--transition-fast); min-height: 32px;
}
.player-row.clickable { cursor: pointer; }
.player-row.clickable:hover { background: var(--color-bg-hover); color: var(--color-text-primary); }
.player-row.selected { background: var(--color-accent-light); color: var(--color-accent); font-weight: var(--font-weight-semibold); }
.player-row.eliminated { color: var(--color-text-muted); text-decoration: line-through; }
.player-row.actual-winner { color: var(--color-brand-live); font-weight: var(--font-weight-semibold); }
.player-row.actual-loser { color: var(--color-text-muted); text-decoration: line-through; }
.player-row.tbd { color: var(--color-text-muted); font-style: italic; }
.seed { font-size: var(--font-size-xs); color: var(--color-warning); font-weight: var(--font-weight-bold); min-width: 20px; }
.name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.check { color: var(--color-brand-live); font-size: var(--font-size-sm); }
.divider { height: 1px; background: var(--color-border); }

.pick-extras { padding: 6px 10px; background: var(--color-bg-secondary); display: flex; flex-direction: column; gap: 4px; }
.extras-label { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.sets-row { display: flex; gap: 4px; flex-wrap: wrap; }
.sets-btn {
    flex: 1 1 auto; min-width: 28px;
    background: var(--color-surface); border: 1px solid var(--color-border);
    border-radius: var(--radius-sm); color: var(--color-text-secondary);
    font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold);
    padding: 3px 6px; cursor: pointer; transition: all var(--transition-fast);
}
.sets-btn:hover { border-color: var(--color-accent); color: var(--color-accent); }
.sets-btn.active {
    background: var(--color-accent); border-color: var(--color-accent); color: var(--color-text-inverse);
}
.sets-btn.disabled { opacity: 0.4; }
.sets-btn.ret-btn { flex: 1 1 100%; margin-top: 2px; }
.sets-btn.ret-btn.active {
    background: var(--color-warning); border-color: var(--color-warning); color: var(--color-text-inverse);
}

.actual-score {
    padding: 4px 10px; font-size: var(--font-size-xs); color: var(--color-text-muted);
    font-family: var(--font-mono); background: var(--color-bg-secondary);
    display: flex; align-items: center; justify-content: space-between; gap: var(--space-2);
}
.actual-tag {
    font-family: var(--font-sans); font-size: 10px; text-transform: uppercase;
    letter-spacing: 0.5px; color: var(--color-text-secondary);
    background: var(--color-surface); border: 1px solid var(--color-border);
    border-radius: var(--radius-sm); padding: 1px 6px;
}
.actual-tag.ret { color: var(--color-warning); border-color: var(--color-warning); }
</style>
