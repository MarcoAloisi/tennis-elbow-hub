<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import tournaments from '@/data/tournaments.json'
import { apiUrl } from '@/config/api'

const props = defineProps({
  server: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['select-player', 'open-match-detail'])

const isSinglesMatch = computed(() => {
  const mode = (props.server.game_info?.mode_display || '').toLowerCase()
  return !mode.includes('doubles')
})

function sideClickable(names) {
  return isSinglesMatch.value && Array.isArray(names) && names.length === 1
}

function onSelectPlayer(name, elo) {
  emit('select-player', { name, elo: typeof elo === 'number' ? elo : 0 })
}

function onOpenMatchDetail() {
  emit('open-match-detail', {
    matchId: props.server.match_id,
    player1: players.value.player1[0],
    player2: players.value.player2?.[0] ?? '',
  })
}

// ============ MATCH DURATION ============
const now = ref(Date.now())
let durationInterval = null

onMounted(() => {
  // Update "now" every 30 seconds for duration display
  durationInterval = setInterval(() => {
    now.value = Date.now()
  }, 30000)
})

onUnmounted(() => {
  if (durationInterval) clearInterval(durationInterval)
})

const matchDuration = computed(() => {
  if (!props.server.creation_time_ms || !props.server.is_started) return null
  
  // Sanity check: creation_time_ms should be a Unix timestamp in milliseconds
  // A valid timestamp for 2020+ would be > 1577836800000 (Jan 1, 2020)
  const creationTime = props.server.creation_time_ms
  const minValidTimestamp = 1577836800000 // Jan 1, 2020 in ms
  
  // If it's too small, it's likely not a Unix timestamp - skip display
  if (creationTime < minValidTimestamp) return null
  
  const elapsed = now.value - creationTime
  
  // If elapsed is negative or too large (> 24 hours), something is wrong
  if (elapsed < 0 || elapsed > 86400000) return null
  
  const minutes = Math.floor(elapsed / 60000)
  if (minutes < 1) return 'Just started'
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}h ${mins}m`
})


// ============ SURFACE DETECTION ============
const surfaceInfo = computed(() => {
  const surfaceName = props.server.surface_name || ''
  const nameLower = surfaceName.toLowerCase()
  
  // Check all tournament categories
  const allTournaments = {
    ...tournaments.grandSlams,
    ...tournaments.masters1000,
    ...tournaments.atp500,
    ...tournaments.atp250,
    ...tournaments.atpFinals,
    ...tournaments.challengers
  }
  
  // Try to find a matching tournament
  for (const [tourName, surface] of Object.entries(allTournaments)) {
    if (nameLower.includes(tourName.toLowerCase())) {
      return { surface }
    }
  }
  
  // Fallback: check keywords
  for (const [surface, keywords] of Object.entries(tournaments.keywords || {})) {
    for (const kw of keywords) {
      if (nameLower.includes(kw.toLowerCase())) {
        return { surface }
      }
    }
  }
  
  return { surface: 'hard' } // Default
})

const surfaceLabel = computed(() => {
  const label = surfaceInfo.value.surface
  return label.charAt(0).toUpperCase() + label.slice(1)
})

// Parse player names from match_name. Doubles rooms are named
// "Host & Partner" (one team); the opposing team isn't named in the feed.
const players = computed(() => {
  const name = props.server.match_name || ''
  const splitSide = (raw) => (raw.includes('/') ? raw.split('/') : [raw])

  for (const sep of [' vs ', ' - ']) {
    if (name.includes(sep)) {
      const [p1Raw, p2Raw] = name.split(sep)
      return { player1: splitSide(p1Raw.trim()), player2: splitSide(p2Raw.trim()) }
    }
  }

  if (name.includes(' & ')) {
    return { player1: name.split(' & ').map((n) => n.trim()), player2: ['Opponents'] }
  }

  // Single player or unknown format
  return { player1: splitSide(name), player2: null }
})

// Score display for the grid, sourced from the server-parsed `live_state`
// (score_parser.py) instead of re-parsing the raw score string here.
// Falls back to empty sets/points and servingPlayer 0 when live_state is
// null (unparseable score) — matches today's worst case for an
// unparseable string.
const scoreDisplay = computed(() => {
  const state = props.server.live_state
  if (!state) {
    return { sets: [], points: { p1: '', p2: '' }, servingPlayer: 0 }
  }
  return {
    sets: state.sets.map(([p1, p2]) => ({ p1, p2 })),
    points: state.current_points
      ? { p1: state.current_points[0], p2: state.current_points[1] }
      : { p1: '', p2: '' },
    servingPlayer: state.server ?? 0,
  }
})

// Live win probability {p1, p2} — null for doubles, bot opponents, or
// matches with 0 ELO on either side.
const winProbability = computed(() => props.server.win_probability)

// ============ H2H POPOVER ============
// Public breakdown of what produced the win% (H2H record + recent form),
// fetched lazily on first click and cached for the lifetime of this card.
const h2hOpen = ref(false)
const h2hLoading = ref(false)
const h2hError = ref('')
const h2hData = ref(null)

function toggleH2h() {
  if (h2hOpen.value) {
    h2hOpen.value = false
    return
  }
  h2hOpen.value = true
  if (h2hData.value || h2hLoading.value) return

  const playerA = players.value.player1[0]
  const playerB = players.value.player2?.[0]
  if (!playerA || !playerB) return

  h2hLoading.value = true
  h2hError.value = ''
  const params = new URLSearchParams({ player_a: playerA, player_b: playerB })
  if (props.server.surface_display) {
    params.set('surface', props.server.surface_display)
  }
  if (props.server.mod) {
    params.set('mod', props.server.mod)
  }

  fetch(apiUrl(`/api/scores/h2h?${params.toString()}`))
    .then((response) => {
      if (!response.ok) throw new Error('Request failed')
      return response.json()
    })
    .then((data) => {
      h2hData.value = data
    })
    .catch(() => {
      h2hError.value = 'Could not load head-to-head data.'
    })
    .finally(() => {
      h2hLoading.value = false
    })
}

// Modal (Teleported to body) instead of an inline popover: an
// absolutely-positioned popover inside the card overlapped neighboring
// cards in the grid whenever it was taller than the gap below it.
function onH2hKeydown(e) {
  if (e.key === 'Escape') h2hOpen.value = false
}

watch(h2hOpen, (open) => {
  if (open) {
    window.addEventListener('keydown', onH2hKeydown)
    document.body.style.overflow = 'hidden'
  } else {
    window.removeEventListener('keydown', onH2hKeydown)
    document.body.style.overflow = ''
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', onH2hKeydown)
  document.body.style.overflow = ''
})

// Surface badge class
const surfaceClass = computed(() => {
  const surface = (props.server.surface_display || props.server.surface_name || '').toLowerCase()
  if (surface.includes('clay')) return 'badge-surface-clay'
  if (surface.includes('grass')) return 'badge-surface-grass'
  if (surface.includes('indoor')) return 'badge-surface-indoor'
  return 'badge-surface-hard'
})

// Format surface name
const surfaceDisplay = computed(() => {
  if (props.server.surface_display) return props.server.surface_display
  
  const name = props.server.surface_name || ''
  const map = {
    'BlueGreenCement': 'Hard Court',
    'Clay': 'Clay',
    'Grass': 'Grass',
    'Indoor': 'Indoor'
  }
  return map[name] || name
})

// Tournament name
const tournamentDisplay = computed(() => {
  if (props.server.tournament_display) return props.server.tournament_display
  const name = props.server.surface_name || ''
  return name.replace(/^\d+\s+/, '') // Fallback cleanup
})

// Mod display (e.g., "XKT v4.2d")
const modDisplay = computed(() => {
  const tagline = props.server.tag_line || ''
  // Basic cleanup if needed, but usually tag_line contains exactly what we want
  // E.g. "XKT v4.2d" or "TE4 v1.0"
  // If it's empty or irrelevant, return null
  if (!tagline || tagline === '0' || tagline === '0.0.0.0') return ''
  return tagline
})

// Sets format display
const setsDisplay = computed(() => {
  return props.server.game_info?.sets_display || ''
})

const isOnlineMode = computed(() => {
  const mode = props.server.game_info?.mode_display || ''
  return mode.trim().toLowerCase() === 'online'
})

</script>

<template>
  <article class="match-card" :class="{ 'is-live': server.is_started }">
    <!-- Header -->
    <div class="match-header">
      <span v-if="server.is_started" class="state state-live"><i class="live-dot"></i>LIVE</span>
      <span v-else class="state state-wait">Waiting</span>

      <span v-if="tournamentDisplay" class="tournament">{{ tournamentDisplay }}</span>
      <span v-else class="tournament">{{ surfaceDisplay }}</span>

      <span class="surface" :class="`surface-${surfaceInfo.surface}`">
        <i class="surface-chip"></i>{{ surfaceLabel }}
      </span>
    </div>

    <!-- Match Grid Layout -->
    <div class="match-grid">
      <div class="player-row">
        <div class="player-info">
          <div class="name-container">
            <span v-if="winProbability" class="winprob-marker winprob-marker-p1"></span>
            <div class="names-wrapper">
              <template v-for="(name, idx) in players.player1" :key="idx">
                <button
                  v-if="sideClickable(players.player1)"
                  type="button"
                  class="player-name clickable"
                  @click.stop="onSelectPlayer(name, server.elo)"
                >
                  {{ name }}
                </button>
                <span v-else class="player-name">{{ name }}</span>
              </template>
            </div>
            <span class="host-badge" title="Match host">Host</span>
          </div>
          <span class="player-elo">ELO {{ server.elo }}</span>
        </div>

        <div class="serving-column">
          <span v-if="scoreDisplay.servingPlayer === 1" class="serving-dot" role="img" aria-label="Serving"></span>
        </div>

        <div class="sets-column">
          <span v-for="(set, idx) in scoreDisplay.sets" :key="idx" class="set-score">{{ set.p1 }}</span>
        </div>

        <div class="points-column" :class="{ 'has-points': server.is_started }">
          <span class="point-score">{{ scoreDisplay.points.p1 }}</span>
        </div>
      </div>

      <div v-if="players.player2" class="player-row">
        <div class="player-info">
          <div class="name-container">
            <span v-if="winProbability" class="winprob-marker winprob-marker-p2"></span>
            <div class="names-wrapper">
              <template v-for="(name, idx) in players.player2" :key="idx">
                <button
                  v-if="sideClickable(players.player2)"
                  type="button"
                  class="player-name clickable"
                  @click.stop="onSelectPlayer(name, server.other_elo)"
                >
                  {{ name }}
                </button>
                <span v-else class="player-name">{{ name }}</span>
              </template>
            </div>
          </div>
          <!-- ponytail: doubles feed sends a fixed 3319 placeholder as other_elo -->
          <span v-if="isSinglesMatch" class="player-elo">ELO {{ server.other_elo }}</span>
        </div>

        <div class="serving-column">
          <span v-if="scoreDisplay.servingPlayer === 2" class="serving-dot" role="img" aria-label="Serving"></span>
        </div>

        <div class="sets-column">
          <span v-for="(set, idx) in scoreDisplay.sets" :key="idx" class="set-score">{{ set.p2 }}</span>
        </div>

        <div class="points-column" :class="{ 'has-points': server.is_started }">
          <span class="point-score">{{ scoreDisplay.points.p2 }}</span>
        </div>
      </div>

      <!-- Win probability: the marker next to each name and the two bar
           segments share a colour per player, so "which % belongs to whom"
           reads from colour, not position. Clicking opens the H2H dialog. -->
      <div v-if="winProbability" class="win-probability-container">
        <button
          type="button"
          class="win-probability-trigger"
          :aria-label="`${Math.round(winProbability.p1 * 100)}% vs ${Math.round(winProbability.p2 * 100)}% win probability, open head-to-head`"
          :aria-expanded="h2hOpen"
          @click.stop="toggleH2h"
        >
          <div class="win-probability-bar">
            <div class="win-probability-segment win-probability-segment-p1" :style="{ width: `${winProbability.p1 * 100}%` }"></div>
            <div class="win-probability-segment win-probability-segment-p2" :style="{ width: `${winProbability.p2 * 100}%` }"></div>
          </div>
          <div class="win-probability-labels">
            <span class="win-probability-label">{{ Math.round(winProbability.p1 * 100) }}%</span>
            <span class="win-probability-label">{{ Math.round(winProbability.p2 * 100) }}%</span>
          </div>
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="h2hOpen" class="h2h-modal-backdrop" @click="h2hOpen = false">
        <div
          class="h2h-modal"
          role="dialog"
          aria-modal="true"
          :aria-label="`Head-to-head: ${players.player1[0]} vs ${players.player2?.[0]}`"
          @click.stop
        >
          <div class="h2h-modal-header">
            <span class="h2h-modal-title">{{ players.player1[0] }} <span class="h2h-modal-vs">vs</span> {{ players.player2?.[0] }}</span>
            <button type="button" class="h2h-modal-close" aria-label="Close" @click="h2hOpen = false">×</button>
          </div>
          <div v-if="h2hLoading" class="h2h-modal-status">Loading…</div>
          <div v-else-if="h2hError" class="h2h-modal-status">{{ h2hError }}</div>
          <template v-else-if="h2hData">
            <div class="h2h-modal-section">
              <span class="h2h-modal-section-title">Head-to-head</span>
              <span v-if="h2hData.h2h.total === 0">No prior matches found.</span>
              <span v-else>
                {{ players.player1[0] }} <strong>{{ h2hData.h2h.wins_a }}</strong> - <strong>{{ h2hData.h2h.wins_b }}</strong> {{ players.player2?.[0] }}
              </span>
              <span v-if="h2hData.h2h.specific_total > 0" class="h2h-modal-subline">
                On {{ server.surface_display }}: {{ h2hData.h2h.specific_wins_a }} - {{ h2hData.h2h.specific_wins_b }}
              </span>
            </div>
            <div class="h2h-modal-section">
              <span class="h2h-modal-section-title">Recent form (30d)</span>
              <span class="h2h-modal-form-row">
                <span class="winprob-marker winprob-marker-p1"></span>
                {{ players.player1[0] }}: {{ h2hData.form_a !== null ? Math.round(h2hData.form_a * 100) + '%' : 'No recent matches' }}
              </span>
              <span class="h2h-modal-form-row">
                <span class="winprob-marker winprob-marker-p2"></span>
                {{ players.player2?.[0] }}: {{ h2hData.form_b !== null ? Math.round(h2hData.form_b * 100) + '%' : 'No recent matches' }}
              </span>
            </div>
          </template>
        </div>
      </div>
    </Teleport>

    <!-- Footer -->
    <div class="match-footer">
      <span class="footer-tag">{{ server.game_info?.mode_display || 'Singles' }}</span>
      <span v-if="matchDuration" class="footer-tag" title="Match duration">{{ matchDuration }}</span>
      <span v-if="modDisplay" class="footer-tag">{{ modDisplay }}</span>
      <span v-if="setsDisplay" class="footer-tag">{{ setsDisplay }}</span>

      <button
        v-if="isSinglesMatch && server.is_started"
        type="button"
        class="game-log-btn"
        @click.stop="onOpenMatchDetail"
      >
        Game log
      </button>
    </div>
  </article>
</template>

<style scoped>
.match-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  transition: background-color var(--transition-base);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  font-variant-numeric: tabular-nums;
}

.match-card:hover,
.match-card.is-live {
  background: var(--color-bg-secondary);
}

.match-card.is-live:hover {
  background: var(--color-bg-tertiary);
}

/* Header */
.match-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}

.state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: none;
  font-weight: 700;
  font-size: var(--font-size-xs);
  letter-spacing: 0.02em;
}

.state-live {
  color: var(--color-brand-live);
}

.state-wait {
  color: var(--color-text-muted);
  font-weight: 600;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-brand-live);
  animation: live-pulse 2s ease-out infinite;
}

@keyframes live-pulse {
  0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.55); }
  70%, 100% { box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
}

.tournament {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.surface {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: none;
}

.surface-chip {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background: var(--color-surface-hard);
}

.surface-clay .surface-chip { background: var(--color-surface-clay); }
.surface-grass .surface-chip { background: var(--color-surface-grass); }
.surface-indoor .surface-chip { background: var(--color-surface-indoor); }

/* Match Grid */
.match-grid {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.player-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 48px;
}

.player-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  overflow: hidden;
}

.name-container {
  display: flex;
  align-items: center;
  gap: 6px;
}

.names-wrapper {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.player-name {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 1.0625rem;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

button.player-name {
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  font: inherit;
  font-weight: 700;
  color: inherit;
  text-align: left;
  cursor: pointer;
  max-width: 100%;
}

button.player-name.clickable:hover,
button.player-name.clickable:focus-visible {
  color: var(--color-brand-primary);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.player-elo {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.host-badge {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-text-primary);
  background: var(--color-bg-tertiary);
  padding: 1px 7px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.serving-column {
  width: 14px;
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: calc(var(--space-2) * -1);
}

.serving-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--color-brand-primary);
}

.sets-column {
  display: flex;
  gap: 4px;
}

.set-score {
  min-width: 28px;
  text-align: center;
  font-family: var(--font-data);
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-text-muted);
}

.points-column {
  min-width: 44px;
  height: 36px;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 6px;
}

.points-column.has-points {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}


.point-score {
  font-family: var(--font-data);
  font-size: 1.25rem;
  font-weight: 700;
}

/* Win % marker: one colour per player, shared with the bar segments */
.winprob-marker {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.winprob-marker-p1 {
  background-color: #60A5FA;
}

.winprob-marker-p2 {
  background-color: #2DD4BF;
}

.win-probability-container {
  position: relative;
  margin-top: var(--space-2);
}

.win-probability-trigger {
  display: block;
  width: 100%;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  text-align: inherit;
  font: inherit;
  color: inherit;
}

.win-probability-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.win-probability-trigger:hover .win-probability-labels {
  color: var(--color-text-primary);
}

.win-probability-bar {
  display: flex;
  height: 4px;
  border-radius: 2px;
  overflow: hidden;
}

.win-probability-segment {
  height: 100%;
  transition: width 0.4s cubic-bezier(0.23, 1, 0.32, 1);
}

.win-probability-segment-p1 {
  background-color: #60A5FA;
}

.win-probability-segment-p2 {
  background-color: #2DD4BF;
}

/* H2H dialog, Teleported to <body> so it can't overlap neighbouring cards */
.h2h-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--space-4);
}

.h2h-modal {
  width: 100%;
  max-width: 360px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  padding: var(--space-4);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.h2h-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.h2h-modal-title {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}

.h2h-modal-vs {
  font-weight: 400;
  color: var(--color-text-secondary);
  margin: 0 2px;
}

.h2h-modal-close {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-md);
  background: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: var(--font-size-xl);
  line-height: 1;
}

.h2h-modal-close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.h2h-modal-status {
  padding: var(--space-2) 0;
}

.h2h-modal-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.h2h-modal-section + .h2h-modal-section {
  margin-top: var(--space-4);
}

.h2h-modal-section-title {
  font-weight: 700;
  color: var(--color-text-primary);
}

.h2h-modal-subline {
  color: var(--color-text-secondary);
}

.h2h-modal-form-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Footer */
.match-footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px var(--space-3);
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.footer-tag + .footer-tag::before {
  content: '·';
  margin-right: var(--space-3);
}

.game-log-btn {
  margin-left: auto;
  min-height: 32px;
  padding: 0 var(--space-2);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: transparent;
  cursor: pointer;
  transition: color var(--transition-fast), background-color var(--transition-fast);
}

.game-log-btn:hover,
.game-log-btn:focus-visible {
  color: var(--color-brand-primary);
  background: var(--color-bg-hover);
}
</style>
