<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import tournaments from '@/data/tournaments.json'

const props = defineProps({
  server: {
    type: Object,
    required: true
  }
})

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
  const elapsed = now.value - props.server.creation_time_ms
  const minutes = Math.floor(elapsed / 60000)
  if (minutes < 1) return 'Just started'
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}h ${mins}m`
})

// ============ ELO DIFFERENCE ============
const eloDiff = computed(() => {
  const elo1 = props.server.elo || 0
  const elo2 = props.server.other_elo || 0
  return elo1 - elo2
})

const player1IsFavorite = computed(() => eloDiff.value > 0)
const player2IsFavorite = computed(() => eloDiff.value < 0)

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
      return { surface, icon: getSurfaceIcon(surface) }
    }
  }
  
  // Fallback: check keywords
  for (const [surface, keywords] of Object.entries(tournaments.keywords || {})) {
    for (const kw of keywords) {
      if (nameLower.includes(kw.toLowerCase())) {
        return { surface, icon: getSurfaceIcon(surface) }
      }
    }
  }
  
  return { surface: 'hard', icon: '🔵' } // Default
})

function getSurfaceIcon(surface) {
  const icons = {
    'clay': '🟠',
    'grass': '🟢',
    'hard': '🔵',
    'indoor': '🏠'
  }
  return icons[surface] || '🔵'
}

// Parse player names from match_name
const players = computed(() => {
  const name = props.server.match_name || ''
  
  // Try " vs " separator
  if (name.includes(' vs ')) {
    const parts = name.split(' vs ')
    const p1Raw = parts[0].trim()
    const p2Raw = parts[1].trim()
    
    // Split doubles names if present (e.g. "Name1/Name2")
    const player1 = p1Raw.includes('/') ? p1Raw.split('/') : [p1Raw]
    const player2 = p2Raw.includes('/') ? p2Raw.split('/') : [p2Raw]
    
    return { player1, player2 }
  }
  
  // Try " - " separator
  if (name.includes(' - ')) {
    const parts = name.split(' - ')
    const p1Raw = parts[0].trim()
    const p2Raw = parts[1].trim()
    
    const player1 = p1Raw.includes('/') ? p1Raw.split('/') : [p1Raw]
    const player2 = p2Raw.includes('/') ? p2Raw.split('/') : [p2Raw]
    
    return { player1, player2 }
  }
  
  // Single player or unknown format
  const p1Raw = name
  const player1 = p1Raw.includes('/') ? p1Raw.split('/') : [p1Raw]
  return { player1, player2: null }
})

// Enhanced score parsing for grid display
const scoreDisplay = computed(() => {
  const score = props.server.score || ''
  // Format: "6/3 4/6 1/1 -- 00:40•" or "6/3 4/6 1/1 -- •00:40"
  
  const parts = score.split(' -- ')
  const setsRaw = parts[0] ? parts[0].trim().split(' ') : []
  let currentGameRaw = parts[1] ? parts[1].trim() : ''
  
  // Detect serving player
  let servingPlayer = 0 // 0 = unknown, 1 = player1, 2 = player2
  if (currentGameRaw.startsWith('•')) {
    servingPlayer = 1
    currentGameRaw = currentGameRaw.substring(1) // Remove the •
  } else if (currentGameRaw.endsWith('•')) {
    servingPlayer = 2
    currentGameRaw = currentGameRaw.substring(0, currentGameRaw.length - 1) // Remove the •
  }

  // Parse sets into { p1: val, p2: val }
  // Example "6/3" -> { p1: "6", p2: "3" }
  const sets = setsRaw.map(setStr => {
    if (setStr.includes('/')) {
      const [p1, p2] = setStr.split('/')
      return { p1, p2 }
    }
    return { p1: setStr, p2: '' }
  }).filter(s => s.p1 || s.p2) // Filter empty entries

  // Parse current game points
  // Example "00:40" or "40:Ad"
  let points = { p1: '', p2: '' }
  if (currentGameRaw.includes(':')) {
    const [p1, p2] = currentGameRaw.split(':')
    points = { p1, p2 }
  } else if (currentGameRaw) {
    // Fallback if no separator
    points = { p1: currentGameRaw, p2: '' }
  }

  return { sets, points, servingPlayer }
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
  <div class="match-card" :class="{ 'is-live': server.is_started }">
    <!-- Header -->
    <div class="match-header">
      <div class="status-badges">
        <span v-if="server.is_started" class="badge badge-live">
          <span class="live-dot-pulse"></span>
          LIVE
        </span>
        <span v-else class="badge badge-waiting">WAITING</span>
        
        <span class="badge badge-surface-icon" :title="surfaceInfo.surface">{{ surfaceInfo.icon }}</span>
        <span v-if="tournamentDisplay" class="badge badge-tournament">{{ tournamentDisplay }}</span>
        <span v-else class="badge" :class="surfaceClass">{{ surfaceDisplay }}</span>
      </div>
    </div>

    <!-- Match Grid Layout -->
    <div class="match-grid">
      <!-- Row 1: Player 1 -->
      <div class="player-row">
        <div class="player-info">
          <div class="name-container">
            <div class="names-wrapper">
              <span v-for="(name, idx) in players.player1" :key="idx" class="player-name">
                {{ name }}
              </span>
            </div>
            <span class="host-badge" title="Match Host">HOST</span>
          </div>
          <span class="player-elo" :class="{ 'elo-favorite': player1IsFavorite }">elo: {{ server.elo }}</span>
        </div>
        
        <!-- Serving Indicator P1 -->
        <div class="serving-column">
          <span v-if="scoreDisplay.servingPlayer === 1" class="serving-dot"></span>
        </div>

        <!-- Sets P1 -->
        <div class="sets-column">
          <span v-for="(set, idx) in scoreDisplay.sets" :key="idx" class="set-score">
            {{ set.p1 }}
          </span>
        </div>

        <!-- Points P1 -->
        <div class="points-column" :class="{ 'has-points': server.is_started }">
          <span class="point-score">{{ scoreDisplay.points.p1 }}</span>
        </div>
      </div>

      <!-- Row 2: Player 2 -->
      <div class="player-row">
        <div class="player-info">
          <div class="name-container">
            <div class="names-wrapper">
              <span v-for="(name, idx) in players.player2" :key="idx" class="player-name">
                {{ name }}
              </span>
            </div>
          </div>
          <span class="player-elo" :class="{ 'elo-favorite': player2IsFavorite }">elo: {{ server.other_elo }}</span>
        </div>

        <!-- Serving Indicator P2 -->
        <div class="serving-column">
          <span v-if="scoreDisplay.servingPlayer === 2" class="serving-dot"></span>
        </div>

        <!-- Sets P2 -->
        <div class="sets-column">
          <span v-for="(set, idx) in scoreDisplay.sets" :key="idx" class="set-score">
            {{ set.p2 }}
          </span>
        </div>

        <!-- Points P2 -->
        <div class="points-column" :class="{ 'has-points': server.is_started }">
          <span class="point-score">{{ scoreDisplay.points.p2 }}</span>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="match-footer">

      <span class="footer-tag" :class="{ 'online-tag': isOnlineMode }">
        <span v-if="isOnlineMode" class="online-dot-pulse"></span>
        {{ server.game_info?.mode_display || 'Singles' }}
      </span>
      
      <!-- Match Duration -->
      <span v-if="matchDuration" class="footer-tag duration-tag" title="Match duration">
        ⏱️ {{ matchDuration }}
      </span>
      
      <!-- Mod Version -->
      <span v-if="modDisplay" class="footer-tag mod-tag">{{ modDisplay }}</span>
      
      <span v-if="setsDisplay" class="footer-tag sets-tag">{{ setsDisplay }}</span>
    </div>
  </div>
</template>

<style scoped>
.match-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  transition: all var(--transition-base);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.match-card:hover {
  border-color: var(--color-brand-primary);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.match-card.is-live {
  border-left: 4px solid var(--color-brand-live);
}

/* Header */
.match-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-badges {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.badge-live {
  background-color: var(--color-brand-live);
  color: var(--color-text-inverse); /* Usually white on green */
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px; /* Slightly more padding */
  font-family: var(--font-heading);
  font-weight: 700;
  font-style: italic; /* Speed/Forward motion */
  text-transform: uppercase;
  letter-spacing: 0.05em; /* Slight spacing for uppercase */
}

.online-dot-pulse {
  width: 6px;
  height: 6px;
  background-color: var(--color-brand-live);
  border-radius: 50%;
  display: inline-block;
  margin-right: 6px;
  animation: pulse 2s infinite ease-in-out;
}

.live-dot-pulse {
  width: 8px;
  height: 8px;
  background-color: white;
  border-radius: 50%;
  animation: pulse 1.5s infinite ease-in-out; /* Improved pulse */
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(255, 255, 255, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0); }
}

.badge-waiting {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-family: var(--font-heading);
  font-weight: 600;
  text-transform: uppercase;
}

/* Match Grid */
.match-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.player-row {
  display: flex;
  align-items: center;
  min-height: 36px; /* Changed from fixed height to min-height for stacked names */
}

/* 1. Player Info Column */
.player-info {
  flex: 1; /* Takes remaining space */
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 140px;
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
}

.player-name {
  font-family: var(--font-heading); /* Inter */
  font-weight: 700; /* Bold for names */
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

.player-elo {
  font-family: var(--font-body);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.host-badge {
  font-size: 8px;
  font-weight: bold;
  color: var(--color-accent);
  background: rgba(99, 102, 241, 0.1);
  padding: 1px 3px;
  border-radius: 2px;
  text-transform: uppercase;
  flex-shrink: 0;
}

/* 2. Serving Column */
.serving-column {
  width: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: 8px;
}

.serving-dot {
  width: 10px;
  height: 10px;
  background-color: var(--color-brand-primary); /* Changed to brand green */
  border-radius: 50%;
}

/* 3. Sets Column */
.sets-column {
  display: flex;
  gap: 12px;
  margin-right: 16px;
}

.set-score {
  width: 20px;
  text-align: center;
  font-family: var(--font-data); /* JetBrains Mono */
  font-size: var(--font-size-lg);
  font-weight: 500;
  color: var(--color-text-primary);
  letter-spacing: var(--letter-spacing-tight);
}

/* 4. Points Column */
.points-column {
  width: 40px;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: transparent; /* Default */
  border-radius: 0;
}

/* Row-spanning background for points */
.match-grid {
  position: relative;
}

/* To create the blue box effect for points, we apply background to the column 
   but we want it to look connected.  */
.points-column.has-points {
  background-color: var(--color-brand-primary); /* Changed to brand green */
  color: var(--color-text-inverse); /* Ensure best contrast, usually white or dark depending on brand color */
}

.player-row:first-child .points-column.has-points {
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  margin-bottom: 1px; /* Tiny gap */
}

.player-row:last-child .points-column.has-points {
  border-bottom-left-radius: 4px;
  border-bottom-right-radius: 4px;
}

.point-score {
  font-family: var(--font-data); /* JetBrains Mono */
  font-size: var(--font-size-lg); 
  font-weight: 700;
  letter-spacing: var(--letter-spacing-tight);
}


/* Footer */
.match-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-3);
}

.footer-tag {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  background: var(--color-bg-secondary);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600; /* Increased weight */
  display: flex; /* Allow dot alignment */
  align-items: center;
}

.online-tag {
    color: var(--color-brand-live);
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.2);
}

.mod-tag {
  color: var(--color-text-primary);
  background-color: rgba(99, 102, 241, 0.05); /* Light Indigo tint */
}

.sets-tag {
  color: var(--color-accent);
  background-color: rgba(99, 102, 241, 0.1);
  margin-left: auto; /* Push to right */
}

.badge-tournament {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 0.75rem;
  font-size: 0.75rem;
  letter-spacing: 0.02em;
  max-width: 180px; /* Restored constraint to prevent grid blowout */
  overflow: hidden; 
  white-space: nowrap;
  flex-shrink: 1; 
  text-overflow: ellipsis; 
}

/* Elo Favorite Highlight */
.elo-favorite {
  color: var(--color-brand-primary) !important;
  font-weight: 700;
}

/* Duration Tag */
.duration-tag {
  color: var(--color-text-secondary);
  background-color: rgba(107, 114, 128, 0.1);
  gap: 4px;
}

/* Surface Icon Badge */
.badge-surface-icon {
  font-size: 1rem;
  padding: 2px 4px;
  background: transparent;
  line-height: 1;
}
</style>
