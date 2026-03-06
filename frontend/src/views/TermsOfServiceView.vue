<script setup lang="ts">
// Static Terms of Service page
</script>

<template>
  <div class="terms-view">
    <div class="terms-content">
      <h1>Terms of Service</h1>
      <p class="last-updated">Last updated: February 27, 2026</p>

      <section>
        <h2>1. Acceptance of Terms</h2>
        <p>
          By accessing and using Tennis Elbow Hub (<strong>tenniselbowhub.live</strong>),
          you agree to be bound by these Terms of Service. If you do not agree
          with any part of these terms, please do not use the website.
        </p>
      </section>

      <section>
        <h2>2. Description of Service</h2>
        <p>
          Tennis Elbow Hub is a free community platform for the video game
          <strong>Tennis Elbow 4</strong> developed by ManaGames. The site provides:
        </p>
        <ul>
          <li>Real-time live scores from online Tennis Elbow 4 matches</li>
          <li>Match log analysis tools with statistics and radar charts</li>
          <li>Information about online competitive tours (XKT, WTSL)</li>
          <li>A gallery of player outfit codes</li>
          <li>Video guides and tutorials</li>
        </ul>
        <p>
          Tennis Elbow Hub is a fan-made community project and is not affiliated
          with, endorsed by, or officially connected to ManaGames or the Tennis
          Elbow franchise.
        </p>
      </section>

      <section>
        <h2>3. User Conduct</h2>
        <p>When using Tennis Elbow Hub, you agree to:</p>
        <ul>
          <li>Use the service only for its intended purpose</li>
          <li>Not attempt to disrupt or interfere with the service's operation</li>
          <li>Not upload malicious, harmful, or inappropriate content</li>
          <li>Not attempt to gain unauthorized access to any part of the service</li>
          <li>Not use automated scripts or bots to scrape data from the site</li>
          <li>Not harass, defame, or cause harm to other community members</li>
        </ul>
      </section>

      <section>
        <h2>4. Uploaded Content</h2>
        <p>
          When you upload match log files (HTML) or WTSL tour logs (CSV) for analysis,
          these files are processed temporarily during your browser session. We do not
          permanently store uploaded files on our servers.
        </p>
        <p>
          For the Outfit Gallery, authorized users may upload outfit images and codes.
          By uploading content, you confirm that you have the right to share it
          and grant Tennis Elbow Hub a non-exclusive, royalty-free license to display
          it on the platform.
        </p>
      </section>

      <section>
        <h2>5. Intellectual Property</h2>
        <p>
          Tennis Elbow 4, its logos, and related game assets are the property of
          <strong>ManaGames</strong>. Tennis Elbow Hub uses game-related names and
          terminology solely for community and informational purposes.
        </p>
        <p>
          The Tennis Elbow Hub website code, design, and original content are the
          property of the Tennis Elbow Hub project. You may not copy, reproduce, or
          distribute the site's code or design without permission.
        </p>
      </section>

      <section>
        <h2>6. Third-Party Services</h2>
        <p>
          Tennis Elbow Hub integrates with the following third-party services:
        </p>
        <ul>
          <li>
            <strong>Google Analytics</strong> — for anonymous usage analytics
          </li>
          <li>
            <strong>Google AdSense</strong> — for contextual advertising
          </li>
          <li>
            <strong>Ko-fi</strong> — for voluntary community donations
          </li>
        </ul>
        <p>
          Each third-party service is governed by its own terms and privacy policies.
          Tennis Elbow Hub is not responsible for the practices of these services.
        </p>
      </section>

      <section>
        <h2>7. Disclaimer of Warranties</h2>
        <p>
          Tennis Elbow Hub is provided <strong>"as is"</strong> and
          <strong>"as available"</strong> without warranties of any kind, either
          express or implied. We do not guarantee that the service will be
          uninterrupted, error-free, or free from harmful components.
        </p>
        <p>
          Live score data is fetched from the Tennis Elbow 4 server list and may
          occasionally be delayed or incomplete. Match analysis results depend on
          the accuracy and format of the uploaded log files.
        </p>
      </section>

      <section>
        <h2>8. Limitation of Liability</h2>
        <p>
          To the fullest extent permitted by applicable law, Tennis Elbow Hub and
          its contributors shall not be liable for any indirect, incidental,
          special, consequential, or punitive damages arising from or related to
          your use of the service.
        </p>
      </section>

      <section>
        <h2>9. Changes to Terms</h2>
        <p>
          We reserve the right to modify these Terms of Service at any time.
          Changes will be posted on this page with an updated revision date.
          Continued use of the service after changes are posted constitutes
          acceptance of the updated terms.
        </p>
      </section>

      <section>
        <h2>10. Governing Law</h2>
        <p>
          These Terms of Service shall be governed by and construed in accordance
          with applicable laws. Any disputes arising from these terms shall be
          resolved through good-faith negotiation.
        </p>
      </section>

      <section>
        <h2>11. Contact</h2>
        <p>
          If you have questions about these Terms of Service, please reach out
          through our community channels on the
          <a href="https://discord.com/invite/PY7hZXZcF6" target="_blank" rel="noopener noreferrer">
            Tennis Elbow 4 Tour Discord</a>
          or email us at
          <a href="mailto:contact@tenniselbowhub.live">contact@tenniselbowhub.live</a>.
        </p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.terms-view {
  min-height: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding-bottom: var(--space-12);
}

.terms-content {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8) var(--space-10);
}

.terms-content h1 {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.last-updated {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: var(--space-8);
  padding-bottom: var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.terms-content section {
  margin-bottom: var(--space-8);
}

.terms-content section:last-child {
  margin-bottom: 0;
}

.terms-content h2 {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.terms-content p {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin-bottom: var(--space-3);
}

.terms-content ul {
  padding-left: var(--space-6);
  margin-bottom: var(--space-3);
}

.terms-content li {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin-bottom: var(--space-1);
}

.terms-content a {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
}

.terms-content a:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .terms-content {
    padding: var(--space-6);
  }

  .terms-content h1 {
    font-size: var(--font-size-2xl);
  }
}
</style>
