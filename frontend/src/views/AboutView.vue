<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="about-view">
    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-badge">🎾 Community Hub</div>
      <h1>Tennis Elbow Hub</h1>
      <p class="hero-subtitle">
        The ultimate companion for <strong>Tennis Elbow 4</strong> players.
        Track live matches, analyze your performance, follow online tours,
        and improve your game — all in one place.
      </p>
      <div class="hero-actions">
        <RouterLink to="/live" class="btn btn-primary">
          <span>📡</span> View Live Scores
        </RouterLink>
        <RouterLink to="/analysis" class="btn btn-secondary">
          <span>📊</span> Analyze Matches
        </RouterLink>
      </div>
    </section>

    <!-- Features Section -->
    <section class="features">
      <h2>What You Can Do</h2>
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">📡</div>
          <h3>Live Scores</h3>
          <p>
            Watch Tennis Elbow 4 online matches unfold in real-time. Our WebSocket-powered
            scoreboard updates every few seconds, showing player names, ELO ratings,
            match scores, surfaces, and tournament details. Filter by surface, search
            by player name, and see today's match statistics at a glance.
          </p>
          <RouterLink to="/live" class="feature-link">Go to Live Scores →</RouterLink>
        </div>

        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <h3>Match Log Analysis</h3>
          <p>
            Upload your Tennis Elbow 4 HTML match logs and get detailed statistical
            breakdowns. View radar charts comparing power, serve accuracy, net game,
            consistency, pressure points, and stamina. Analyze head-to-head records,
            filter by opponent, surface, or tournament, and track your improvement
            over time with win rate calculations.
          </p>
          <RouterLink to="/analysis" class="feature-link">Go to Match Analysis →</RouterLink>
        </div>

        <div class="feature-card">
          <div class="feature-icon">🌐</div>
          <h3>Online Tours</h3>
          <p>
            Stay informed about the competitive Tennis Elbow 4 scene. Browse online
            tours like XKT and WTSL, check tournament schedules, read the rules,
            and connect with the community. Upload WTSL tour CSV files to see player
            rankings, statistical leaders, and complete match histories.
          </p>
          <RouterLink to="/online-tours" class="feature-link">Go to Online Tours →</RouterLink>
        </div>

        <div class="feature-card">
          <div class="feature-icon">🎬</div>
          <h3>Video Guides</h3>
          <p>
            Learn the ropes with curated video tutorials for Tennis Elbow 4 online play.
            Whether you're a newcomer looking to set up your first online match or an
            experienced player looking for advanced strategies, our guide collection
            has something for every level.
          </p>
          <RouterLink to="/guides" class="feature-link">Go to Guides →</RouterLink>
        </div>
      </div>
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
            Tennis Elbow Hub does not create user accounts or permanently store uploaded
            match logs. Your analysis data is processed in the browser session and is
            not saved on our servers after the session ends. We use Google Analytics for
            anonymous usage statistics — see our
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
  max-width: 900px;
  margin: 0 auto;
}

/* Hero */
.hero {
  text-align: center;
  padding: var(--space-12) 0 var(--space-16);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-12);
}

.hero-badge {
  display: inline-block;
  padding: var(--space-2) var(--space-4);
  background: var(--color-accent-light);
  color: var(--color-accent);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--space-6);
  letter-spacing: 0.02em;
}

.hero h1 {
  font-size: 3.5rem;
  font-weight: 800;
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.hero-subtitle {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  max-width: 600px;
  margin: 0 auto var(--space-8);
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  gap: var(--space-4);
  justify-content: center;
  flex-wrap: wrap;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-lg);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  transition: all var(--transition-fast);
  text-decoration: none;
}

.btn-primary {
  background: var(--color-accent);
  color: #fff;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.4);
}

.btn-secondary {
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.btn-secondary:hover {
  background: var(--color-bg-hover);
  transform: translateY(-1px);
}

/* Features */
.features {
  margin-bottom: var(--space-12);
}

.features h2 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-8);
  text-align: center;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-6);
}

.feature-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  transition: all var(--transition-fast);
}

.feature-card:hover {
  border-color: var(--color-accent);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.feature-icon {
  font-size: 2rem;
  margin-bottom: var(--space-3);
}

.feature-card h3 {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.feature-card p {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: var(--space-4);
}

.feature-link {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-accent);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.feature-link:hover {
  text-decoration: underline;
}

/* TE4 Section */
.about-te4 {
  margin-bottom: var(--space-12);
  padding: var(--space-8);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
}

.about-te4 h2 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-6);
}

.te4-content p {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin-bottom: var(--space-4);
}

.te4-content p:last-child {
  margin-bottom: 0;
}

/* FAQ */
.faq {
  margin-bottom: var(--space-12);
}

.faq h2 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-8);
  text-align: center;
}

.faq-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.faq-item {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: border-color var(--transition-fast);
}

.faq-item[open] {
  border-color: var(--color-accent);
}

.faq-item summary {
  padding: var(--space-4) var(--space-6);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  cursor: pointer;
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: background var(--transition-fast);
}

.faq-item summary:hover {
  background: var(--color-bg-hover);
}

.faq-item summary::after {
  content: '+';
  font-size: 1.25rem;
  font-weight: 300;
  color: var(--color-text-muted);
  transition: transform var(--transition-fast);
}

.faq-item[open] summary::after {
  content: '−';
}

.faq-item summary::-webkit-details-marker {
  display: none;
}

.faq-item p {
  padding: 0 var(--space-6) var(--space-5);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.8;
}

.faq-item a {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
}

.faq-item a:hover {
  text-decoration: underline;
}

/* Responsive */
@media (max-width: 768px) {
  .hero h1 {
    font-size: 2.5rem;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .hero-actions {
    flex-direction: column;
    align-items: center;
  }
}
</style>
