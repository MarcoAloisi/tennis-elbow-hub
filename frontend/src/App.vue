<script setup>
import { RouterView, RouterLink } from 'vue-router'
import ThemeToggle from './components/common/ThemeToggle.vue'
</script>

<template>
  <div class="app-container">
    <!-- Header -->
    <header class="app-header">
      <div class="header-content">
        <div class="logo">
          <span class="logo-icon">🎾</span>
          <span class="logo-text">Tennis Elbow Hub</span>
        </div>
        
        <nav class="nav-links">
          <RouterLink to="/" class="nav-link" active-class="active">
            <span class="nav-icon">📊</span>
            Live Scores
          </RouterLink>
          <RouterLink to="/analysis" class="nav-link" active-class="active">
            <span class="nav-icon">📈</span>
            Match Analysis
          </RouterLink>
        </nav>
        
        <div class="header-actions">
          <ThemeToggle />
        </div>
      </div>
    </header>
    
    <!-- Main Content -->
    <main class="app-main">
      <RouterView />
    </main>
    
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

.logo-icon {
  font-size: 1.75rem;
}

.logo-text {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-brand-primary);
  /* background: var(--color-accent-gradient); Removed broken gradient */
}

.nav-links {
  display: flex;
  gap: var(--space-2);
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

.app-main {
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
}

.app-footer {
  text-align: center;
  padding: var(--space-6);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  border-top: 1px solid var(--color-border);
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
