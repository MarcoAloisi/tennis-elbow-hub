<script setup>
// Static privacy policy page — no dynamic data needed
</script>

<template>
  <div class="privacy-view">
    <div class="privacy-content">
      <h1>Privacy Policy</h1>
      <p class="last-updated">Last updated: February 11, 2026</p>

      <section>
        <h2>Introduction</h2>
        <p>
          Tennis Elbow Hub ("we", "us", "our") operates the website
          <strong>tenniselbowhub.live</strong>. This page informs you of our policies
          regarding the collection, use, and disclosure of information when you use
          our service.
        </p>
      </section>

      <section>
        <h2>Information We Collect</h2>
        <p>
          Tennis Elbow Hub does not require user accounts or registration. We do not
          collect personally identifiable information such as names, email addresses,
          or passwords.
        </p>
        <h3>Uploaded Files</h3>
        <p>
          When you use the Match Log Analysis feature, you upload HTML match log files
          from Tennis Elbow 4. These files are processed in your browser session to
          generate statistics. <strong>We do not permanently store uploaded files on
          our servers.</strong> Once your session ends, the data is no longer retained.
        </p>
        <h3>Automatically Collected Data</h3>
        <p>
          We use Google Analytics (GA4) to collect anonymous usage data, including:
        </p>
        <ul>
          <li>Pages visited and time spent on each page</li>
          <li>Browser type and operating system</li>
          <li>Referring website</li>
          <li>Approximate geographic location (country/region level)</li>
          <li>Device type (desktop, mobile, tablet)</li>
        </ul>
        <p>
          This data is aggregated and anonymized. It helps us understand how the site
          is used and improve the experience.
        </p>
      </section>

      <section>
        <h2>Cookies</h2>
        <p>
          Tennis Elbow Hub and our third-party partners use cookies and similar
          technologies for the following purposes:
        </p>
        <h3>Essential Cookies</h3>
        <p>
          We use local storage to remember your theme preference (dark/light mode).
          No personal data is stored.
        </p>
        <h3>Analytics Cookies</h3>
        <p>
          Google Analytics uses cookies to distinguish unique users and throttle request
          rates. These cookies do not contain personal information. You can opt out of
          Google Analytics by installing the
          <a href="https://tools.google.com/dlpage/gaoptout" target="_blank" rel="noopener noreferrer">
            Google Analytics Opt-out Browser Add-on</a>.
        </p>
        <h3>Advertising Cookies</h3>
        <p>
          We use Google AdSense to display advertisements. Google may use cookies to
          serve ads based on your prior visits to this website or other websites. You
          can opt out of personalized advertising by visiting
          <a href="https://www.google.com/settings/ads" target="_blank" rel="noopener noreferrer">
            Google's Ads Settings</a>.
        </p>
      </section>

      <section>
        <h2>Third-Party Services</h2>
        <p>We use the following third-party services:</p>
        <ul>
          <li>
            <strong>Google Analytics (GA4)</strong> — for anonymous usage analytics.
            <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">
              Google Privacy Policy</a>
          </li>
          <li>
            <strong>Google AdSense</strong> — for displaying advertisements.
            <a href="https://policies.google.com/technologies/ads" target="_blank" rel="noopener noreferrer">
              Google Ads Policy</a>
          </li>
          <li>
            <strong>Ko-fi</strong> — for voluntary donations.
            <a href="https://ko-fi.com/privacy" target="_blank" rel="noopener noreferrer">
              Ko-fi Privacy Policy</a>
          </li>
        </ul>
      </section>

      <section>
        <h2>Data Retention</h2>
        <p>
          We do not store personal data. Analytics data is retained by Google according
          to their data retention policies. Uploaded match logs are not stored beyond
          the active browser session.
        </p>
      </section>

      <section>
        <h2>Children's Privacy</h2>
        <p>
          Our service is not directed to children under 13. We do not knowingly collect
          information from children under 13.
        </p>
      </section>

      <section>
        <h2>Your Rights</h2>
        <p>
          Under applicable data protection laws (including GDPR), you have the right to:
        </p>
        <ul>
          <li>Access the personal data we hold about you</li>
          <li>Request deletion of your data</li>
          <li>Opt out of analytics and personalized advertising</li>
          <li>Withdraw consent at any time</li>
        </ul>
        <p>
          Since we do not collect personal data or require accounts, most of these
          rights are automatically fulfilled.
        </p>
      </section>

      <section>
        <h2>Changes to This Policy</h2>
        <p>
          We may update this Privacy Policy from time to time. Changes will be posted
          on this page with an updated revision date. We encourage you to review this
          page periodically.
        </p>
      </section>

      <section>
        <h2>Contact</h2>
        <p>
          If you have questions about this Privacy Policy, please reach out through
          our community channels on the
          <a href="https://discord.com/invite/PY7hZXZcF6" target="_blank" rel="noopener noreferrer">
            Tennis Elbow 4 Tour Discord</a>.
        </p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.privacy-view {
  min-height: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding-bottom: var(--space-12);
}

.privacy-content {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8) var(--space-10);
}

.privacy-content h1 {
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

.privacy-content section {
  margin-bottom: var(--space-8);
}

.privacy-content section:last-child {
  margin-bottom: 0;
}

.privacy-content h2 {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.privacy-content h3 {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-top: var(--space-4);
  margin-bottom: var(--space-2);
}

.privacy-content p {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin-bottom: var(--space-3);
}

.privacy-content ul {
  padding-left: var(--space-6);
  margin-bottom: var(--space-3);
}

.privacy-content li {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin-bottom: var(--space-1);
}

.privacy-content a {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
}

.privacy-content a:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .privacy-content {
    padding: var(--space-6);
  }

  .privacy-content h1 {
    font-size: var(--font-size-2xl);
  }
}
</style>
