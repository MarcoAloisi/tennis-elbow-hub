<!-- frontend/src/components/predictions/BracketMatch.vue -->
<script setup lang="ts">
import type { DrawMatch, PlayerInfo } from '@/stores/predictions'

const props = defineProps<{
    match: DrawMatch
    pickedWinner: string | null
    pickedScore: string | undefined
    readonly: boolean
}>()

const emit = defineEmits<{
    pick: [matchId: string, winner: string, score: string | undefined]
}>()

function selectPlayer(player: PlayerInfo) {
    if (props.readonly || player.name === 'TBD') return
    emit('pick', props.match.id, player.name, props.pickedScore)
}

function onScoreInput(e: Event) {
    const score = (e.target as HTMLInputElement).value
    if (props.pickedWinner) {
        emit('pick', props.match.id, props.pickedWinner, score || undefined)
    }
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

const ROUND_EXACT_PTS: Record<string, number> = {
    R1: 30, R2: 50, R3: 70, QF: 100, SF: 150, F: 200
}
const exactPts = ROUND_EXACT_PTS[props.match.round] ?? 30
</script>

<template>
    <div class="bracket-match">
        <!-- Player 1 -->
        <div
            class="player-row"
            :class="{
                selected: isSelected(match.player1),
                eliminated: isEliminated(match.player1),
                'actual-winner': readonly && isActualWinner(match.player1),
                'actual-loser': readonly && isActualLoser(match.player1),
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
                'actual-winner': readonly && isActualWinner(match.player2),
                'actual-loser': readonly && isActualLoser(match.player2),
                tbd: match.player2.name === 'TBD',
                clickable: !readonly && match.player2.name !== 'TBD',
            }"
            @click="selectPlayer(match.player2)"
        >
            <span class="seed">{{ match.player2.seed ? `(${match.player2.seed})` : '' }}</span>
            <span class="name">{{ match.player2.name }}</span>
            <span v-if="isSelected(match.player2)" class="check">✓</span>
        </div>

        <!-- Score input (shown when a winner is picked and not readonly) -->
        <div v-if="!readonly && pickedWinner" class="score-area">
            <div class="score-label">Score optional · exact = +{{ exactPts }} pts</div>
            <input
                class="score-input"
                type="text"
                :value="pickedScore || ''"
                placeholder="e.g. 6/3 6/2"
                maxlength="20"
                @input="onScoreInput"
            />
        </div>

        <!-- Readonly: show actual score if available -->
        <div v-if="readonly && match.score" class="actual-score">
            {{ match.score }}
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
.bracket-match:hover {
    border-color: var(--color-border-hover);
}
.player-row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: 6px 10px;
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    transition: background var(--transition-fast), color var(--transition-fast);
    min-height: 32px;
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
.score-area { padding: 6px 10px; background: var(--color-bg-secondary); }
.score-label { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-bottom: 3px; }
.score-input {
    width: 100%;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    color: var(--color-text-primary);
    font-size: var(--font-size-xs);
    padding: 3px 7px;
    outline: none;
    font-family: var(--font-mono);
}
.score-input:focus { border-color: var(--color-accent); }
.actual-score {
    padding: 4px 10px;
    font-size: var(--font-size-xs);
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    background: var(--color-bg-secondary);
}
</style>
