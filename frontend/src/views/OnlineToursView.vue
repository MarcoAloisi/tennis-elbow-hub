<script setup>
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import tourData from '@/data/onlineTours.json'

const route = useRoute()

// Get current tour from route
const currentTourKey = computed(() => {
  return route.path.includes('/wtsl') ? 'wtsl' : 'xkt'
})

const currentTour = computed(() => tourData.tours[currentTourKey.value])

// Get tour data for tabs
const xktTour = tourData.tours.xkt
const wtslTour = tourData.tours.wtsl
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

        <!-- Links -->
        <div class="tour-links">
          <h3>Quick Links</h3>
          <div class="links-grid">
            <a 
              v-for="(link, key) in currentTour.links" 
              :key="key"
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

/* Links */
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

.link-label {
  flex: 1;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.link-icon-img {
  width: 24px;
  height: 24px;
  object-fit: contain;
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
}
</style>
