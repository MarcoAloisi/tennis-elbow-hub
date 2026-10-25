<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import MatchCard from '@/components/scores/MatchCard.vue'
import { useScoresStore } from '@/stores/scores'

const router = useRouter()
const store = useScoresStore()

// Fetched on the client only, so the prerendered page ships without a stale board.
onMounted(() => {
  store.fetchScores()
})

const liveMatches = computed(() => store.servers.filter((s) => s.is_started))
const heroMatches = computed(() => liveMatches.value.slice(0, 3))

function openLive() {
  router.push('/live')
}
</script>

<template>
  <div class="about-view">
    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-copy">
        <h1>Tennis Elbow 4 online matches, live.</h1>
        <p class="hero-subtitle">
          Follow the XKT, WTSL and Vanilla boards as they play, upload your match logs for a
          full breakdown, and find the tour that fits your game.
        </p>
        <div class="hero-actions">
          <RouterLink to="/live" class="btn btn-primary">Open live scores</RouterLink>
          <RouterLink to="/analysis" class="btn btn-quiet">Analyze a match log</RouterLink>
        </div>
      </div>

      <div v-if="heroMatches.length" class="hero-board" aria-label="Matches playing now">
        <MatchCard
          v-for="server in heroMatches"
          :key="server.match_id"
          :server="server"
          @select-player="openLive"
          @open-match-detail="openLive"
        />
      </div>
    </section>

    <!-- Destinations -->
    <section class="destinations" aria-labelledby="destinations-heading">
      <h2 id="destinations-heading">What you can do here</h2>
      <ul>
        <li>
          <RouterLink to="/live" class="destination">
            <span class="destination-title">Live scores</span>
            <span class="destination-text">
              Watch Tennis Elbow 4 online matches unfold in real time. The WebSocket-powered
              scoreboard updates every few seconds, showing player names, ELO ratings, match
              scores, surfaces, and tournament details. Filter by surface, search by player
              name, track the most active players, view daily matches played, and see
              today's match statistics at a glance.
            </span>
            <span class="destination-meta">
              <template v-if="liveMatches.length"><i class="dot"></i>{{ liveMatches.length }} playing now</template>
              <template v-else>Open board</template>
            </span>
          </RouterLink>
        </li>
        <li>
          <RouterLink to="/analysis" class="destination">
            <span class="destination-title">Match log analysis</span>
            <span class="destination-text">
              Upload your Tennis Elbow 4 HTML match logs and get AI-powered match review
              analysis with detailed statistical breakdowns. Explore historical data charts,
              view radar charts comparing power, serve accuracy, net game, consistency,
              pressure points, and stamina. Analyze head-to-head records, filter by opponent,
              surface, or tournament, and track your improvement over time with win rate
              calculations.
            </span>
            <span class="destination-meta">Upload logs</span>
          </RouterLink>
        </li>
        <li>
          <RouterLink to="/online-tours" class="destination">
            <span class="destination-title">Online tours</span>
            <span class="destination-text">
              Stay informed about the competitive Tennis Elbow 4 scene. Browse online tours
              like XKT and WTSL, check tournament schedules, read the rules, and connect with
              the community. Upload WTSL tour CSV files to see player rankings, statistical
              leaders, and complete match histories.
            </span>
            <span class="destination-meta">XKT and WTSL</span>
          </RouterLink>
        </li>
        <li>
          <RouterLink to="/guides" class="destination">
            <span class="destination-title">Guides</span>
            <span class="destination-text">
              Learn the ropes with curated video tutorials for Tennis Elbow 4 online play.
              Whether you're a newcomer setting up your first online match or an experienced
              player looking for advanced strategies, the guide collection has something for
              every level.
            </span>
            <span class="destination-meta">Read and watch</span>
          </RouterLink>
        </li>
      </ul>
    </section>

    <!-- What is TE4 Section -->
    <section class="about-te4">
      <h2>What is Tennis Elbow 4?</h2>
      <div class="te4-content">
        <p>
          <strong>Tennis Elbow 4</strong> is a tennis simulation video game developed by
          <strong>ManaGames</strong>. Known for its realistic gameplay mechanics, deep
          career modes, and competitive online multiplayer, Tennis Elbow 4 has built a
          dedicated community of players worldwide. The game features accurate ball physics,
          strategic gameplay, and an extensive modding scene that brings real-world players,
          tournaments, and surfaces into the game.
        </p>
        <p>
          Online multiplayer in Tennis Elbow 4 supports singles and doubles matches,
          competitive and cooperative modes, and a built-in ELO rating system to match
          players of similar skill. Community-organized tours like <strong>XKT</strong> and
          <strong>WTSL</strong> bring an extra layer of competitive structure with seasonal
          rankings, scheduled tournaments, and detailed statistics tracking.
        </p>
        <p>
          Tennis Elbow Hub was created to enhance the online experience by providing
          tools that the base game doesn't offer — real-time scoreboards visible to
          spectators, detailed post-match analytics, and a central hub for the
          competitive community.
        </p>
      </div>
    </section>

    <!-- FAQ Section -->
    <section class="faq">
      <h2>Frequently Asked Questions</h2>
      <div class="faq-list">
        <details class="faq-item" open>
          <summary>How does the Live Scores feature work?</summary>
          <p>
            Tennis Elbow Hub connects to the Tennis Elbow 4 server list and fetches match
            data in real time. When players create online matches, they appear on our
            scoreboard with live score updates, player ELO ratings, surface information,
            and match duration. The data refreshes every few seconds via WebSocket,
            so you always see the latest state.
          </p>
        </details>

        <details class="faq-item">
          <summary>How do I upload a match log for analysis?</summary>
          <p>
            After playing online matches in Tennis Elbow 4, the game generates HTML match
            log files. Go to the <strong>Match Log Analysis</strong> tab, click the upload
            area, and select your match log file. The system will parse it and display
            detailed statistics including radar charts, win rates, and performance metrics
            for each match.
          </p>
        </details>

        <details class="faq-item">
          <summary>What are the XKT and WTSL tours?</summary>
          <p>
            XKT and WTSL are community-organized competitive tours for Tennis Elbow 4
            online players. They feature scheduled tournaments, seasonal rankings, and
            structured competition. Visit the <strong>Online Tours</strong> tab to learn
            more about each tour's rules, schedules, and how to join.
          </p>
        </details>

        <details class="faq-item">
          <summary>Is Tennis Elbow Hub free to use?</summary>
          <p>
            Yes! Tennis Elbow Hub is completely free. All features — live scores, match
            analysis, tour information, and guides — are available to everyone. If you
            enjoy the site, you can support its development through the Ko-fi donation
            button.
          </p>
        </details>

        <details class="faq-item">
          <summary>Does Tennis Elbow Hub store my data?</summary>
          <p>
            Accounts are optional. Live scores, match analysis and guides work without
            one. You only need an account for community features such as uploading
            outfits and managing a profile, and signing up stores your display name and
            email address. Uploaded match logs are read by our server to produce your
            statistics and are not saved to our database. We use Google Analytics for
            anonymous usage statistics and Google AdSense for advertising. See our
            <RouterLink to="/privacy-policy">Privacy Policy</RouterLink> for details.
          </p>
        </details>
      </div>
    </section>
  </div>
</template>

<style scoped>
.about-view {
  min-height: 100%;
}

/* Hero */
.hero {
  display: grid;
  grid-template-columns: minmax(0, 6fr) minmax(0, 5fr);
  gap: var(--space-12);
  align-items: center;
  padding: var(--space-12) 0 var(--space-6);
}

.hero:not(:has(.hero-board)) {
  grid-template-columns: minmax(0, 1fr);
}

.hero h1 {
  font-size: clamp(2rem, 4.4vw, 3.75rem);
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.035em;
  text-wrap: balance;
}

.hero-subtitle {
  font-size: 1.1875rem;
  color: var(--color-text-secondary);
  max-width: 44ch;
  margin-top: var(--space-5);
  line-height: 1.55;
}

.hero-actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  align-items: center;
  margin-top: var(--space-8);
}

.hero-board {
  display: grid;
  gap: var(--space-4);
}

.hero-board > :nth-child(2) {
  margin-left: var(--space-8);
}

.hero-board > :nth-child(3) {
  margin-left: var(--space-16);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  padding: 0 var(--space-6);
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  transition: background-color var(--transition-fast), color var(--transition-fast), filter var(--transition-fast), transform 100ms;
}

.btn:active {
  transform: translateY(1px);
}

.btn-primary {
  background: var(--color-brand-primary);
  color: var(--color-text-inverse);
}

.btn-primary:hover {
  color: var(--color-text-inverse);
  filter: brightness(1.08);
}

.btn-quiet {
  color: var(--color-text-secondary);
}

.btn-quiet:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

.btn-secondary {
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
}

.btn-secondary:hover {
  background: var(--color-bg-tertiary);
}

/* Destinations */
.destinations {
  margin-top: var(--space-16);
}

.destinations h2,
.about-te4 h2,
.faq h2 {
  font-size: 1.5rem;
  letter-spacing: -0.01em;
}

.destinations ul {
  margin-top: var(--space-4);
  display: grid;
  gap: 2px;
}

.destination {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) auto;
  gap: var(--space-6);
  align-items: start;
  padding: var(--space-5) var(--space-4);
  border-radius: var(--radius-lg);
  color: inherit;
  transition: background-color var(--transition-fast);
}

.destination:hover {
  background: var(--color-bg-card);
  color: inherit;
}

.destination-title {
  font-family: var(--font-heading);
  font-size: 1.375rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--color-text-primary);
}

.destination-text {
  max-width: 62ch;
  color: var(--color-text-secondary);
}

.destination-meta {
  font-variant-numeric: tabular-nums;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding-top: 4px;
  white-space: nowrap;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.destination:hover .destination-meta {
  color: var(--color-brand-primary);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-brand-live);
}

/* TE4 Section */
.about-te4 {
  margin-top: var(--space-16);
}

.te4-content {
  margin-top: var(--space-4);
  max-width: 68ch;
}

.te4-content p {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.75;
  margin-bottom: var(--space-4);
}

.te4-content p:last-child {
  margin-bottom: 0;
}

.te4-content strong {
  color: var(--color-text-primary);
  font-weight: 600;
}

/* FAQ */
.faq {
  margin-top: var(--space-16);
}

.faq-list {
  display: grid;
  gap: 2px;
  margin-top: var(--space-4);
  max-width: 820px;
}

.faq-item {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.faq-item summary {
  padding: var(--space-4) var(--space-5);
  min-height: 56px;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  cursor: pointer;
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  transition: background-color var(--transition-fast);
}

.faq-item summary:hover {
  background: var(--color-bg-secondary);
}

.faq-item summary::after {
  content: '+';
  font-size: 1.25rem;
  font-weight: 300;
  color: var(--color-text-muted);
}

.faq-item[open] summary::after {
  content: '\2212';
}

.faq-item summary::-webkit-details-marker {
  display: none;
}

.faq-item p {
  padding: 0 var(--space-5) var(--space-5);
  max-width: 70ch;
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.faq-item a {
  color: var(--color-text-primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* Responsive */
@media (max-width: 1024px) {
  .hero {
    grid-template-columns: 1fr;
    gap: var(--space-8);
    padding-top: var(--space-6);
  }

  .hero-board > :nth-child(n) {
    margin-left: 0;
  }
}

@media (max-width: 768px) {
  .destination {
    grid-template-columns: 1fr auto;
    gap: var(--space-2) var(--space-4);
    padding: var(--space-4) var(--space-2);
  }

  .destination-text {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .hero-actions .btn-primary {
    flex: 1 1 100%;
  }
}
</style>
