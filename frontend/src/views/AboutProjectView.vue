<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="about-project-view">
    <div class="about-content">
      <h1>About Tennis Elbow Hub</h1>
      <p class="lead">
        Tennis Elbow Hub is an independent, fan-made website for players of
        <strong>Tennis Elbow 4</strong>, the tennis simulation by ManaGames. It is
        not affiliated with or endorsed by ManaGames.
      </p>

      <section>
        <h2>Who runs it</h2>
        <p>
          The site is built and maintained by Marco, an independent developer and
          member of the Tennis Elbow 4 online community. The project started in
          January 2026 to give online players the tools the game does not include:
          a public scoreboard, post-match statistics and a home for guides and tour
          information.
        </p>
      </section>

      <section>
        <h2>Where the content comes from</h2>
        <ul>
          <li>
            <strong>Live scores</strong> are read from the Tennis Elbow 4 online
            server list and refreshed every few seconds. Player ELO ratings are the
            ones the game itself reports.
          </li>
          <li>
            <strong>Match analysis</strong> works on the HTML match logs you upload
            yourself. Nothing is analysed unless you provide a log.
          </li>
          <li>
            <strong>Guides</strong> are written or curated by the site team and
            published under the author's name. Video guides embed the author's own
            YouTube upload.
          </li>
          <li>
            <strong>Outfits</strong> are submitted by registered community members,
            each credited to its uploader.
          </li>
          <li>
            <strong>Tour information</strong> covers the community-run XKT and WTSL
            tours and links to their official channels.
          </li>
        </ul>
      </section>

      <section>
        <h2>How the site is funded</h2>
        <p>
          Hosting is paid for by voluntary donations through Ko-fi and by
          advertising. See the <RouterLink to="/privacy-policy">Privacy Policy</RouterLink>
          for how advertising and analytics cookies are used.
        </p>
      </section>

      <section>
        <h2>Corrections and contact</h2>
        <p>
          Found a wrong stat, an outdated guide or a broken page? Use the
          <RouterLink to="/contact">contact form</RouterLink>, email
          <a href="mailto:contact@tenniselbowhub.live">contact@tenniselbowhub.live</a>,
          or write in the
          <a href="https://discord.com/invite/PY7hZXZcF6" target="_blank" rel="noopener noreferrer">
            Tennis Elbow 4 Tour Discord</a>.
          Guide submissions and corrections from the community are welcome.
        </p>
        <p>
          Updates and videos are also posted on
          <a href="https://www.instagram.com/te4__tv/" target="_blank" rel="noopener noreferrer">Instagram (@te4__tv)</a>.
        </p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.about-project-view {
  min-height: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding-bottom: var(--space-12);
}

.about-content {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8) var(--space-10);
}

.about-content h1 {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
}

.lead {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin-bottom: var(--space-8);
  padding-bottom: var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.about-content section {
  margin-bottom: var(--space-8);
}

.about-content section:last-child {
  margin-bottom: 0;
}

.about-content h2 {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
}

.about-content p,
.about-content li {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin-bottom: var(--space-3);
}

.about-content ul {
  padding-left: var(--space-6);
}

.about-content a {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
}

.about-content a:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .about-content {
    padding: var(--space-6);
  }

  .about-content h1 {
    font-size: var(--font-size-2xl);
  }
}
</style>
