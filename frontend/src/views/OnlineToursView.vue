<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import tourData from '@/data/onlineTours.json'
import { useTourLogsStore } from '@/stores/tourLogs'

const route = useRoute()
const tourLogsStore = useTourLogsStore()

// Get current tour from route
const currentTourKey = computed(() => {
  return route.path.includes('/wtsl') ? 'wtsl' : 'xkt'
})

const currentTour = computed(() => tourData.tours[currentTourKey.value])

// Get tour data for tabs
const xktTour = tourData.tours.xkt
const wtslTour = tourData.tours.wtsl

// Fetch tour logs data when on WTSL tab (for latest date display)
onMounted(() => {
  if (currentTourKey.value === 'wtsl') {
    tourLogsStore.fetchData()
  }
})

watch(currentTourKey, (newKey) => {
  if (newKey === 'wtsl' && !tourLogsStore.data.length) {
    tourLogsStore.fetchData()
  }
})
</script>

<template>
  <div class="online-tours-view">
    <!-- Header -->
    <div class="page-header">
      <h1>Online Tours</h1>
      <p class="intro-text">
        Tennis Elbow 4 has two main competitive online tours: <strong>XKT</strong> and <strong>WTSL</strong>. 
        Each tour follows specific rules and settings for fair competitive play. 
        Select a tour below to learn more and find registration links.
      </p>
    </div>

    <!-- Sub-tabs -->
    <div class="tour-tabs">
      <RouterLink 
        to="/online-tours/xkt" 
        class="tour-tab"
        :class="{ active: currentTourKey === 'xkt' }"
      >
        <img :src="xktTour.logo" :alt="xktTour.name" class="tab-logo" />
        XKT Tour
      </RouterLink>
      <RouterLink 
        to="/online-tours/wtsl" 
        class="tour-tab"
        :class="{ active: currentTourKey === 'wtsl' }"
      >
        <img :src="wtslTour.logo" :alt="wtslTour.name" class="tab-logo" />
        WTSL Tour
      </RouterLink>
    </div>

    <!-- Tour Content -->
    <div class="tour-content">
      <div class="tour-card">
        <!-- Tour Header -->
        <div class="tour-header">
          <img :src="currentTour.logo" :alt="currentTour.name" class="tour-logo" />
          <h2>{{ currentTour.name }}</h2>
        </div>

        <!-- Description -->
        <p class="tour-description">{{ currentTour.description }}</p>

        <!-- Settings -->
        <div class="tour-settings">
          <h3>Tour Settings</h3>
          <div class="settings-grid">
            <div 
              v-for="setting in currentTour.settings" 
              :key="setting.label"
              class="setting-item"
            >
              <span class="setting-label">{{ setting.label }}</span>
              <span class="setting-value">{{ setting.value }}</span>
            </div>
          </div>
        </div>

        <!-- Discord Join Section -->
        <div class="discord-section">
          <h3>
            <svg class="discord-header-logo" viewBox="0 -28.5 256 256" xmlns="http://www.w3.org/2000/svg">
              <path d="M216.856 16.597A208.502 208.502 0 00164.042 0c-2.275 4.113-4.933 9.645-6.766 14.046-19.692-2.961-39.203-2.961-58.533 0-1.832-4.4-4.55-9.933-6.846-14.046a207.809 207.809 0 00-52.855 16.638C5.618 67.147-3.443 116.4 1.087 164.956c22.169 16.555 43.653 26.612 64.775 33.193A161.094 161.094 0 0079.735 175.3a136.413 136.413 0 01-21.846-10.632 108.636 108.636 0 005.356-4.237c42.122 19.702 87.89 19.702 129.51 0a131.66 131.66 0 005.355 4.237 136.07 136.07 0 01-21.886 10.653c4.006 8.02 8.638 15.67 13.873 22.848 21.142-6.58 42.646-16.637 64.815-33.213 5.316-56.288-9.08-105.09-38.056-148.36zM85.474 135.095c-12.645 0-23.015-11.805-23.015-26.18s10.149-26.2 23.015-26.2c12.867 0 23.236 11.804 23.015 26.2.02 14.375-10.148 26.18-23.015 26.18zm85.051 0c-12.645 0-23.015-11.805-23.015-26.18s10.148-26.2 23.015-26.2c12.867 0 23.236 11.804 23.015 26.2 0 14.375-10.148 26.18-23.015 26.18z" fill="#5865F2"/>
            </svg>
            Join Discord
          </h3>
          <div class="discord-grid">
            <template v-for="(link, key) in currentTour.links" :key="'discord-' + key">
              <a 
                v-if="link.icon.startsWith('/') && key !== 'discordXKT' && key !== 'main' && key !== 'youtube'"
                :href="link.url"
                target="_blank"
                rel="noopener noreferrer"
                class="discord-card"
              >
                <div class="discord-badge">JOIN TOUR</div>
                <img 
                  :src="link.icon" 
                  :alt="link.label" 
                  class="discord-icon" 
                />
                <div class="discord-content">
                  <span class="discord-label">{{ link.label }}</span>
                  <span class="discord-sublabel">Join the community on Discord</span>
                </div>
                <svg class="discord-logo-arrow" viewBox="0 -28.5 256 256" xmlns="http://www.w3.org/2000/svg">
                  <path d="M216.856 16.597A208.502 208.502 0 00164.042 0c-2.275 4.113-4.933 9.645-6.766 14.046-19.692-2.961-39.203-2.961-58.533 0-1.832-4.4-4.55-9.933-6.846-14.046a207.809 207.809 0 00-52.855 16.638C5.618 67.147-3.443 116.4 1.087 164.956c22.169 16.555 43.653 26.612 64.775 33.193A161.094 161.094 0 0079.735 175.3a136.413 136.413 0 01-21.846-10.632 108.636 108.636 0 005.356-4.237c42.122 19.702 87.89 19.702 129.51 0a131.66 131.66 0 005.355 4.237 136.07 136.07 0 01-21.886 10.653c4.006 8.02 8.638 15.67 13.873 22.848 21.142-6.58 42.646-16.637 64.815-33.213 5.316-56.288-9.08-105.09-38.056-148.36zM85.474 135.095c-12.645 0-23.015-11.805-23.015-26.18s10.149-26.2 23.015-26.2c12.867 0 23.236 11.804 23.015 26.2.02 14.375-10.148 26.18-23.015 26.18zm85.051 0c-12.645 0-23.015-11.805-23.015-26.18s10.148-26.2 23.015-26.2c12.867 0 23.236 11.804 23.015 26.2 0 14.375-10.148 26.18-23.015 26.18z" fill="currentColor"/>
                </svg>
              </a>
            </template>
          </div>
        </div>

        <!-- Quick Links -->
        <div class="tour-links">
          <h3>Quick Links</h3>
          <div class="links-grid">
            <template v-for="(link, key) in currentTour.links" :key="key">
              <a 
                v-if="!link.icon.startsWith('/') || key === 'discordXKT' || key === 'main' || key === 'youtube'"
                :href="link.url"
                target="_blank"
                rel="noopener noreferrer"
                class="link-card"
              >
                <img 
                  v-if="link.icon.startsWith('/')" 
                  :src="link.icon" 
                  :alt="link.label" 
                  class="link-icon-img" 
                />
                <span v-else class="link-icon">{{ link.icon }}</span>
                <span class="link-label">{{ link.label }}</span>
                <span class="link-arrow">→</span>
              </a>
            </template>
          </div>

          <!-- Tour Logs Link (WTSL only) -->
          <div v-if="currentTourKey === 'wtsl'" class="tour-stats-section">
            <h3>Tour Statistics</h3>
            <RouterLink 
              to="/tour-logs" 
              class="link-card tour-logs-highlight"
            >
              <span class="link-icon">📊</span>
              <div class="tour-logs-content">
                <span class="link-label">Tour Logs & Player Stats</span>
                <span class="link-sublabel">View match history and detailed statistics</span>
              </div>
              <span class="link-arrow">→</span>
            </RouterLink>
          </div>
        </div>

        <!-- Guide Video Link -->
        <div class="tour-guide">
          <h3>Getting Started</h3>
          <RouterLink 
            :to="`/guides?filter=${currentTourKey}`" 
            class="guide-link"
          >
            <span class="guide-icon">🎬</span>
            <div class="guide-content">
              <span class="guide-title">Watch Setup Guide</span>
              <span class="guide-subtitle">Learn how to play {{ currentTour.name }} online</span>
            </div>
            <span class="guide-arrow">→</span>
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.online-tours-view {
  min-height: 100%;
}

.page-header {
  margin-bottom: var(--space-6);
}

.page-header h1 {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.intro-text {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.7;
  max-width: 700px;
}

.intro-text strong {
  color: var(--color-accent);
  font-weight: var(--font-weight-semibold);
}

/* Tour Tabs */
.tour-tabs {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
  border-bottom: 2px solid var(--color-border);
  padding-bottom: var(--space-2);
}

.tour-tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  background: transparent;
  border: 2px solid transparent;
  border-bottom: none;
  transition: all var(--transition-fast);
  margin-bottom: -2px;
}

.tour-tab:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

.tour-tab.active {
  color: var(--color-accent);
  background: var(--color-surface);
  border-color: var(--color-border);
  border-bottom-color: var(--color-surface);
}

.tab-logo {
  width: 28px;
  height: 28px;
  object-fit: contain;
  border-radius: var(--radius-sm);
}

/* Tour Content */
.tour-content {
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.tour-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.tour-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.tour-logo {
  width: 48px;
  height: 48px;
  object-fit: contain;
  border-radius: var(--radius-md);
}

.tour-header h2 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.tour-description {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

/* Settings */
.tour-settings h3,
.tour-links h3 {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
}

.settings-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}

.setting-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--color-bg-secondary);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
}

.setting-label {
  color: var(--color-text-secondary);
}

.setting-value {
  color: var(--color-accent);
  font-weight: var(--font-weight-semibold);
}

/* Discord Section */
.discord-section {
  margin-bottom: var(--space-6);
}

.discord-section h3 {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.discord-header-logo {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
}

/* Discord Join Cards - Prominent CTA */
.discord-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.discord-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-5);
  padding: var(--space-7, 2rem) var(--space-6);
  padding-top: var(--space-8, 2.5rem);
  background: linear-gradient(135deg, rgba(88, 101, 242, 0.15), rgba(88, 101, 242, 0.05));
  border: 2px solid rgba(88, 101, 242, 0.4);
  border-radius: var(--radius-lg);
  transition: all var(--transition-fast);
  overflow: hidden;
  min-height: 110px;
}

.discord-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, transparent, rgba(88, 101, 242, 0.1));
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.discord-card:hover {
  background: linear-gradient(135deg, rgba(88, 101, 242, 0.25), rgba(88, 101, 242, 0.1));
  border-color: rgba(88, 101, 242, 0.7);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(88, 101, 242, 0.2);
}

.discord-card:hover::before {
  opacity: 1;
}

.discord-badge {
  position: absolute;
  top: 0;
  right: 0;
  background: linear-gradient(135deg, #5865F2, #7289da);
  color: white;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  padding: var(--space-1) var(--space-3);
  border-radius: 0 var(--radius-lg) 0 var(--radius-md);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.discord-icon {
  width: 56px;
  height: 56px;
  object-fit: contain;
  border-radius: var(--radius-md);
  border: 2px solid rgba(88, 101, 242, 0.3);
  background: var(--color-bg-secondary);
  padding: var(--space-2);
  flex-shrink: 0;
}

.discord-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.discord-label {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.discord-sublabel {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.discord-logo-arrow {
  width: 40px;
  height: 40px;
  color: #5865F2;
  flex-shrink: 0;
  transition: transform var(--transition-fast);
}

.discord-card:hover .discord-logo-arrow {
  transform: scale(1.15);
}

/* Regular Links */
.links-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-3);
}

.link-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.link-card:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-accent);
  transform: translateX(4px);
}

.link-icon {
  font-size: 1.5rem;
}

.link-icon-img {
  width: 24px;
  height: 24px;
  object-fit: contain;
  border-radius: var(--radius-sm);
}

.link-label {
  flex: 1;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.link-arrow {
  color: var(--color-accent);
  font-size: 1.25rem;
  transition: transform var(--transition-fast);
}

.link-card:hover .link-arrow {
  transform: translateX(4px);
}

/* Tour Logs Highlight Card */
.tour-stats-section {
  margin-top: var(--space-6);
  padding-top: var(--space-6);
  border-top: 1px solid var(--color-border);
}

.tour-stats-section h3 {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
}

.tour-logs-highlight {
  background: linear-gradient(135deg, rgba(59, 177, 67, 0.1), rgba(59, 177, 67, 0.05));
  border: 1px solid rgba(59, 177, 67, 0.3);
  padding: var(--space-5);
}

.tour-logs-highlight:hover {
  background: linear-gradient(135deg, rgba(59, 177, 67, 0.2), rgba(59, 177, 67, 0.1));
  border-color: var(--color-brand-primary);
}

.tour-logs-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.link-sublabel {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: normal;
}

.tour-stats-footer {
  margin-top: var(--space-3);
  text-align: right;
}

.last-updated {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-style: italic;
}

/* Guide Link Section */
.tour-guide {
  margin-top: var(--space-6);
  padding-top: var(--space-6);
  border-top: 1px solid var(--color-border);
}

.tour-guide h3 {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
}

.guide-link {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.1));
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: var(--radius-lg);
  transition: all var(--transition-fast);
}

.guide-link:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(168, 85, 247, 0.2));
  border-color: var(--color-accent);
  transform: translateX(4px);
}

.guide-icon {
  font-size: 2rem;
}

.guide-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.guide-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.guide-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.guide-arrow {
  color: var(--color-accent);
  font-size: 1.5rem;
  transition: transform var(--transition-fast);
}

.guide-link:hover .guide-arrow {
  transform: translateX(4px);
}

/* Responsive */
@media (max-width: 640px) {
  .tour-tabs {
    flex-direction: column;
    border-bottom: none;
    gap: var(--space-2);
  }

  .tour-tab {
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    margin-bottom: 0;
  }

  .tour-tab.active {
    border-color: var(--color-accent);
    background: var(--color-accent-light);
  }

  .settings-grid {
    flex-direction: column;
  }

  .links-grid {
    grid-template-columns: 1fr;
  }

  .discord-grid {
    grid-template-columns: 1fr;
  }

  .discord-icon {
    width: 40px;
    height: 40px;
  }
}
</style>
