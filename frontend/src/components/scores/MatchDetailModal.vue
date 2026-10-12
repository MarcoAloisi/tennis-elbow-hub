<script setup lang="ts">
import { computed, nextTick, ref, toRef, watch } from 'vue'
import { apiUrl } from '@/config/api'
import { useModalAccessibility } from '@/composables/useModalAccessibility'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import type { GameServer, MatchRef } from '@/stores/scores'
import { buildSets, isBreak, isMatchOver, type GameEntry, type Side } from '@/utils/gameLog'
import { X } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  match: MatchRef | null
  liveServer?: GameServer
}>()

const emit = defineEmits<{ close: [] }>()

useModalAccessibility(toRef(props, 'open'), {
  onClose: () => emit('close'),
  containerSelector: '#match-detail-dialog',
})

const sides: Side[] = [1, 2]
const panelId = 'match-detail-panel'

const games = ref<GameEntry[]>([])
const isLoading = ref(false)
const hasError = ref(false)
const selectedSet = ref<number | null>(null)
let requestId = 0

async function load(matchId: string) {
  const id = ++requestId
  isLoading.value = true
  try {
    const res = await fetch(apiUrl(`/api/scores/${encodeURIComponent(matchId)}/games`))
    if (!res.ok) throw new Error(`Request failed: ${res.status}`)
    const data: GameEntry[] = await res.json()
    if (id !== requestId) return
    games.value = data
    hasError.value = false
  } catch {
    if (id !== requestId) return
    if (!games.value.length) hasError.value = true
  } finally {
    if (id === requestId) isLoading.value = false
  }
}

watch(
  () => [props.open, props.match?.matchId, props.liveServer?.score] as const,
  ([open, matchId], previous) => {
    if (!open || !matchId) {
      requestId++
      isLoading.value = false
      return
    }
    if (!previous || previous[0] !== open || previous[1] !== matchId) {
      games.value = []
      hasError.value = false
      selectedSet.value = null
    }
    load(matchId)
  },
  { immediate: true }
)

const liveState = computed(() => {
  const server = props.liveServer
  const state = server?.live_state
  if (!server || !state || isMatchOver(state.sets_won, server.game_info.nb_set)) return null
  return state
})

const liveServerSide = computed<Side | null>(() => {
  const server = liveState.value?.server
  return server === 1 || server === 2 ? server : null
})

const sets = computed(() => {
  const state = liveState.value
  const liveSet = state
    ? { setNumber: state.sets_won[0] + state.sets_won[1] + 1, score: state.current_set_games }
    : null
  return buildSets(games.value, liveSet)
})

const activeSet = computed(
  () => sets.value.find((s) => s.setNumber === selectedSet.value) ?? sets.value[sets.value.length - 1]
)

function playerName(side: Side): string {
  return side === 1 ? (props.match?.player1 ?? '') : (props.match?.player2 ?? '')
}

function gamePill(game: GameEntry): 'TB' | 'Break' | null {
  if (game.is_tiebreak) return 'TB'
  return isBreak(game) ? 'Break' : null
}

function isSetWinner(score: [number, number], side: Side): boolean {
  return score[side - 1] > score[2 - side]
}

function onTabKeydown(event: KeyboardEvent) {
  const count = sets.value.length
  const current = sets.value.findIndex((s) => s.setNumber === activeSet.value?.setNumber)
  let next: number
  if (event.key === 'ArrowRight') next = (current + 1) % count
  else if (event.key === 'ArrowLeft') next = (current - 1 + count) % count
  else if (event.key === 'Home') next = 0
  else if (event.key === 'End') next = count - 1
  else return
  event.preventDefault()
  const tablist = event.currentTarget as HTMLElement
  selectedSet.value = sets.value[next].setNumber
  nextTick(() => tablist.querySelector<HTMLElement>('[aria-selected="true"]')?.focus())
}
</script>

<template>
  <div
    v-if="open && match"
    id="match-detail-dialog"
    class="modal-overlay"
    role="dialog"
    aria-modal="true"
    :aria-label="`Game log: ${match.player1} vs ${match.player2}`"
    @click.self="emit('close')"
  >
    <div class="detail-modal">
      <div class="detail-modal-header">
        <h2>{{ match.player1 }} <span class="detail-vs">vs</span> {{ match.player2 }}</h2>
        <button type="button" class="modal-close" aria-label="Close" @click="emit('close')">
          <X :size="20" />
        </button>
      </div>

      <div class="detail-modal-body">
        <div v-if="isLoading && !games.length" class="detail-status">
          <LoadingSpinner size="md" />
          <p>Loading game log…</p>
        </div>

        <template v-else-if="activeSet">
          <div class="scoreboard">
            <span v-if="liveState" class="live-badge"><span class="live-dot" aria-hidden="true"></span>Live</span>
            <table class="score-table">
              <thead>
                <tr>
                  <th scope="col"><span class="sr-only">Player</span></th>
                  <th v-for="set in sets" :key="set.setNumber" scope="col" class="score-cell">
                    <span aria-hidden="true">{{ set.setNumber }}</span>
                    <span class="sr-only">Set {{ set.setNumber }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="side in sides" :key="side">
                  <th scope="row" class="score-name">
                    <span class="score-name-text">{{ playerName(side) }}</span>
                    <span
                      v-if="liveServerSide === side"
                      class="ball"
                      role="img"
                      :aria-label="`${playerName(side)} serving`"
                    ></span>
                  </th>
                  <td
                    v-for="set in sets"
                    :key="set.setNumber"
                    class="score-cell"
                    :class="{ 'score-live': set.live, 'score-won': !set.live && isSetWinner(set.score, side) }"
                  >
                    {{ set.score[side - 1] }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="set-tabs" role="tablist" aria-label="Sets" @keydown="onTabKeydown">
            <button
              v-for="set in sets"
              :id="`match-detail-tab-${set.setNumber}`"
              :key="set.setNumber"
              type="button"
              role="tab"
              class="set-tab"
              :class="{ active: set.setNumber === activeSet.setNumber }"
              :aria-selected="set.setNumber === activeSet.setNumber"
              :aria-controls="panelId"
              :tabindex="set.setNumber === activeSet.setNumber ? 0 : -1"
              @click="selectedSet = set.setNumber"
            >
              <span class="set-tab-name">Set {{ set.setNumber }}</span> <span class="set-tab-score">{{ set.score[0] }}-{{ set.score[1] }}</span>
            </button>
          </div>

          <div
            :id="panelId"
            role="tabpanel"
            tabindex="0"
            class="set-panel"
            :aria-labelledby="`match-detail-tab-${activeSet.setNumber}`"
          >
            <ol class="game-list">
              <li v-for="game in activeSet.games" :key="game.game_number" class="game">
                <div class="game-head">
                  <span class="game-score">{{ game.p1_games }} · {{ game.p2_games }}</span>
                  <div v-for="side in sides" :key="side" class="side" :class="`side-${side}`">
                    <span
                      v-if="game.server === side"
                      class="ball"
                      role="img"
                      :aria-label="`${playerName(side)} served`"
                    ></span>
                    <span
                      v-if="game.winner === side && gamePill(game)"
                      class="pill"
                      :class="game.is_tiebreak ? 'pill-tb' : 'pill-break'"
                    >{{ gamePill(game) }}<span class="sr-only">, {{ playerName(side) }}</span></span>
                  </div>
                </div>
                <p class="game-trail">
                  <template v-if="game.points?.length">{{ `${game.points.join(', ')}, ` }}</template>
                  <strong class="game-result">{{ isBreak(game) ? 'Break' : 'Game' }} {{ game.p1_games }}-{{ game.p2_games }}</strong>
                </p>
              </li>

              <li v-if="activeSet.live && liveState" class="game game-current">
                <p class="current-label"><span class="live-dot" aria-hidden="true"></span>Current game</p>
                <div class="game-head">
                  <span class="game-score">{{ liveState.current_set_games[0] }} · {{ liveState.current_set_games[1] }}</span>
                  <div v-for="side in sides" :key="side" class="side" :class="`side-${side}`">
                    <span
                      v-if="liveServerSide === side"
                      class="ball"
                      role="img"
                      :aria-label="`${playerName(side)} serving`"
                    ></span>
                  </div>
                </div>
                <p v-if="liveState.current_points" class="game-trail">
                  <strong class="game-result">{{ liveState.current_points[0] }}-{{ liveState.current_points[1] }}</strong>
                </p>
              </li>
            </ol>
          </div>

          <p class="detail-caption">Point trail is best effort, polling can miss points.</p>
        </template>

        <p v-else-if="hasError" class="detail-status detail-error">Could not load the game log.</p>

        <p v-else class="detail-status">No game history recorded for this match.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-modal {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 580px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.detail-modal-header h2 {
  min-width: 0;
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--color-text-primary);
  margin: 0;
  overflow-wrap: anywhere;
}

.detail-vs {
  font-size: var(--font-size-xs);
  font-weight: 400;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.modal-close {
  flex-shrink: 0;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.modal-close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.detail-modal-body {
  padding: var(--space-4) var(--space-6);
  overflow-y: auto;
}

.detail-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-8) 0;
  color: var(--color-text-muted);
  text-align: center;
}

.detail-error {
  color: var(--color-error);
}

.scoreboard {
  position: relative;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-3) var(--space-4);
}

.live-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
  padding: 1px var(--space-2);
  border-radius: var(--radius-full);
  background: var(--color-success-light);
  color: var(--color-brand-live);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.live-dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-brand-live);
  animation: live-pulse 1.5s infinite ease-in-out;
}

@keyframes live-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-dot {
    animation: none;
  }
}

.score-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.score-table th,
.score-table td {
  padding: var(--space-1) 0;
  font-weight: var(--font-weight-normal);
}

.score-table thead th {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.score-name {
  text-align: left;
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  white-space: nowrap;
}

.score-name-text {
  display: inline-block;
  max-width: calc(100% - 20px);
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: middle;
}

.score-name .ball {
  margin-left: var(--space-2);
  vertical-align: middle;
}

.score-cell {
  width: 2.25rem;
  text-align: center;
  font-family: var(--font-data);
  color: var(--color-text-secondary);
}

.score-table tbody .score-won {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-bold);
}

.score-table tbody .score-live {
  color: var(--color-accent);
}

.ball {
  display: inline-block;
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-accent);
  box-shadow: 0 0 0 1px var(--color-surface);
}

.set-tabs {
  display: flex;
  margin-top: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  overflow-x: auto;
  overflow-y: hidden;
}

.set-tab {
  flex: 1 1 0;
  min-width: 3.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--space-2) var(--space-2);
  background: transparent;
  border: 0;
  border-bottom: 2px solid transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font: inherit;
}

.set-tab:hover {
  color: var(--color-text-primary);
}

.set-tab:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}

.set-tab.active {
  color: var(--color-text-primary);
  border-bottom-color: var(--color-accent);
}

.set-tab-name {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.set-tab-score {
  font-family: var(--font-data);
  font-size: var(--font-size-sm);
}

.game-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.game {
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border);
}

.game-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  column-gap: var(--space-3);
}

.game-score {
  grid-column: 2;
  grid-row: 1;
  font-family: var(--font-data);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.side {
  grid-row: 1;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.side-1 {
  grid-column: 1;
  justify-content: flex-end;
}

.side-2 {
  grid-column: 3;
  justify-content: flex-start;
}

.pill {
  padding: 1px var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.pill-break {
  color: var(--color-error);
  background: var(--color-error-light);
  border: 1px solid var(--color-error-border);
}

.pill-tb {
  color: var(--color-accent);
  background: var(--color-accent-light);
  border: 1px solid transparent;
}

.game-trail {
  margin: var(--space-2) 0 0;
  text-align: center;
  font-family: var(--font-data);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  overflow-wrap: anywhere;
}

.game-result {
  color: var(--color-accent);
  font-weight: var(--font-weight-bold);
}

.current-label {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-2);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-secondary);
}

.detail-caption {
  margin-top: var(--space-4);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

@media (max-width: 480px) {
  .detail-modal {
    max-height: 92vh;
  }

  .detail-modal-header,
  .detail-modal-body {
    padding-left: var(--space-4);
    padding-right: var(--space-4);
  }

  .game-head {
    column-gap: var(--space-2);
  }
}
</style>
