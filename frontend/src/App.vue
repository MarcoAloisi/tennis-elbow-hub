<script setup>
import { RouterView, RouterLink } from 'vue-router'
import ThemeToggle from './components/common/ThemeToggle.vue'
import AdSidebar from './components/common/AdSidebar.vue'
import KofiWidget from './components/common/KofiWidget.vue'
</script>

<template>
  <div class="app-container">
    <!-- Header -->
    <header class="app-header">
      <div class="header-content">
        <div class="logo">
          <img src="/logo_fav.svg" alt="Tennis Elbow Hub" class="logo-image" />
          <span class="logo-text">Tennis Elbow Hub</span>
        </div>
        
        <nav class="nav-links">
          <RouterLink to="/" class="nav-link" active-class="active">
            <span class="nav-icon">🎾</span>
            Live Scores
          </RouterLink>
          <div class="nav-divider"></div>
          <RouterLink to="/analysis" class="nav-link" active-class="active">
            <span class="nav-icon">📊</span>
            Match Log Analysis
          </RouterLink>
          <div class="nav-divider"></div>
          <RouterLink to="/online-tours" class="nav-link" active-class="active">
            <span class="nav-icon">🌐</span>
            Online Tours
          </RouterLink>
          <div class="nav-divider"></div>
          <RouterLink to="/guides" class="nav-link" active-class="active">
            <span class="nav-icon">🎬</span>
            Guides
          </RouterLink>
          <div class="nav-divider"></div>
          <RouterLink to="/tour-logs" class="nav-link" active-class="active">
            <span class="nav-icon">🏆</span>
            WTSL Tour Logs
          </RouterLink>
        </nav>
        
        <div class="header-actions">
          <ThemeToggle />
        </div>
      </div>
    </header>
    
    <!-- Content Wrapper with Ads -->
    <div class="content-wrapper">
      <!-- Left Ad Rail -->
      <aside class="ad-rail left">
        <AdSidebar side="left" />
      </aside>

      <!-- Main Content -->
      <main class="app-main">
        <RouterView />
      </main>

      <!-- Right Ad Rail -->
      <aside class="ad-rail right">
        <AdSidebar side="right" />
      </aside>
    </div>
    
    <!-- Ko-fi Widget -->
    <!-- REPLACE 'tenniselbowhub' WITH YOUR ACTUAL KO-FI USERNAME -->
    <KofiWidget username="marcolinote4" />

    <!-- Footer -->
    <footer class="app-footer">
      <p>Tennis Elbow Hub &copy; 2025 - Tennis Elbow 4 Live Scores & Analysis</p>
    </footer>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  background: var(--color-surface); /* Clear separation from body bg */
  border-bottom: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm); /* Added shadow for lift */
  backdrop-filter: blur(10px);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px; /* Reduced from 1400px for better focus */
  margin: 0 auto;
  padding: var(--space-4) var(--space-6);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.logo-image {
  height: 40px;
  width: auto;
}

.logo-text {
  font-size: 1.5rem; /* Increased from XL to roughly 2XL */
  font-weight: 800; /* Extra bolc */
  color: var(--color-brand-primary);
  /* background: var(--color-accent-gradient); Removed broken gradient */
}

.nav-links {
  display: flex;
  align-items: center; /* Ensure divider is centered */
  gap: var(--space-2);
}

.nav-divider {
  width: 2px; /* Thicker */
  height: 24px;
  background-color: var(--color-text-secondary); /* Darker/More visible */
  opacity: 0.3; /* Slight transparency to blend but stay visible */
  margin: 0 var(--space-2);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

.nav-link.active {
  color: var(--color-accent);
  background: var(--color-accent-light);
}

.nav-icon {
  font-size: 1.1rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* Layout Grid */
.content-wrapper {
  display: flex;
  justify-content: center;
  flex: 1; /* Take remaining height */
  width: 100%;
}

.app-main {
  width: 100%;
  max-width: 1200px;
  padding: var(--space-8) var(--space-6);
  /* Removed margin: 0 auto as flex handles centering/layout */
}

/* Ad Rails */
.ad-rail {
  display: none; /* Hidden by default */
  width: 200px; /* Base width for rail */
  padding-top: var(--space-8);
}

/* Responsive Ads: Show only on large screens */
@media (min-width: 1600px) {
  .ad-rail {
    display: flex;
  }

  .ad-rail.left {
    justify-content: flex-end;
    padding-right: var(--space-4);
  }

  .ad-rail.right {
    justify-content: flex-start;
    padding-left: var(--space-4);
  }
}

.app-footer {
  text-align: center;
  padding: var(--space-6);
  color: var(--color-text-secondary); /* Slightly sharper text */
  font-size: var(--font-size-sm);
  background: var(--color-surface); /* Match Header */
  border-top: 1px solid var(--color-border);
  position: relative; /* Ensure it stacks correctly */
  z-index: 10;
}

/* Responsive */
@media (max-width: 768px) {
  .header-content {
    flex-wrap: wrap;
    gap: var(--space-4);
  }
  
  .nav-links {
    order: 3;
    width: 100%;
    justify-content: center;
  }
  
  .logo-text {
    font-size: var(--font-size-lg);
  }
}
</style>
