<script setup>
import { computed, onMounted } from 'vue'
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import ThemeToggle from './components/common/ThemeToggle.vue'
import AdSidebar from './components/common/AdSidebar.vue'
import KofiWidget from './components/common/KofiWidget.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  authStore.initAuth()
})

const showAds = computed(() => {
  const noAdRoutes = ['/', '/privacy-policy']
  return !noAdRoutes.includes(route.path)
})

const handleUpdateName = async () => {
  const currentName = authStore.user?.user_metadata?.display_name || authStore.user?.email?.split('@')[0] || ''
  const newName = prompt('Enter your new Display Name:', currentName)
  if (newName !== null && newName.trim() !== '') {
    try {
      await authStore.updateDisplayName(newName.trim())
      // Name updates instantly due to reactivity in Pinia
    } catch (err) {
      alert('Failed to update name: ' + err.message)
    }
  }
}
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
          <RouterLink to="/live" class="nav-link" active-class="active">
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
          <RouterLink to="/outfit-gallery" class="nav-link" active-class="active">
            <span class="nav-icon">👕</span>
            Outfit Gallery
          </RouterLink>
          <div class="nav-divider"></div>
          <RouterLink to="/guides" class="nav-link" active-class="active">
            <span class="nav-icon">🎬</span>
            Guides
          </RouterLink>
        </nav>
        
        <div class="header-actions">
          <div class="nav-divider"></div>
          
          <div v-if="!authStore.loading" class="auth-buttons">
            <template v-if="authStore.user">
              <span 
                class="user-greeting is-clickable" 
                @click="handleUpdateName" 
                title="Click to set your Display Name"
              >
                Hi, {{ authStore.user?.user_metadata?.display_name || authStore.user?.email.split('@')[0] || 'Admin' }}
              </span>
              <button class="btn-logout" @click="authStore.logout()" title="Log Out">
                <span class="logout-icon">🚪</span>
              </button>
            </template>
            <template v-else>
              <button class="btn-login" @click="router.push('/login')">Log In</button>
            </template>
          </div>
          <ThemeToggle />
        </div>
      </div>
    </header>
    
    <!-- Content Wrapper with Ads -->
    <div class="content-wrapper">
      <!-- Left Ad Rail -->
      <aside v-if="showAds" class="ad-rail left">
        <AdSidebar side="left" />
      </aside>

      <!-- Main Content -->
      <main class="app-main">
        <RouterView />
      </main>

      <!-- Right Ad Rail -->
      <aside v-if="showAds" class="ad-rail right">
        <AdSidebar side="right" />
      </aside>
    </div>
    
    <!-- Ko-fi Widget -->
    <!-- REPLACE 'tenniselbowhub' WITH YOUR ACTUAL KO-FI USERNAME -->
    <KofiWidget username="marcolinote4" />

    <!-- Footer -->
    <footer class="app-footer">
      <p>Tennis Elbow Hub &copy; 2025–2026 — Tennis Elbow 4 Live Scores & Analysis</p>
      <div class="footer-links">
        <RouterLink to="/">About</RouterLink>
        <span class="footer-sep">·</span>
        <RouterLink to="/privacy-policy">Privacy Policy</RouterLink>
      </div>
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
  gap: var(--space-2);
}

.auth-buttons {
  display: flex;
  align-items: center;
}

.user-greeting {
  font-family: var(--font-heading);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
  transition: color var(--transition-fast);
}

.user-greeting.is-clickable {
  cursor: pointer;
}

.user-greeting.is-clickable:hover {
  color: var(--color-text-primary);
  text-decoration: underline;
}

.btn-login {
  display: flex;
  align-items: center;
  background: transparent;
  color: var(--color-text-secondary);
  border: none;
  padding: var(--space-3) var(--space-2);
  border-radius: var(--radius-md);
  font-family: var(--font-heading);
  font-weight: var(--font-weight-medium);
  font-size: 1rem;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.btn-login:hover {
  color: var(--color-text-primary);
}

.btn-logout {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid transparent;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-base);
}

.logout-icon {
  font-size: 1.1rem;
  line-height: 1;
}

.btn-logout:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
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
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  position: relative;
  z-index: 10;
}

.footer-links {
  margin-top: var(--space-2);
  display: flex;
  justify-content: center;
  gap: var(--space-2);
}

.footer-links a {
  color: var(--color-text-muted);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.footer-links a:hover {
  color: var(--color-accent);
}

.footer-sep {
  color: var(--color-text-muted);
  opacity: 0.5;
}

/* Responsive */
@media (max-width: 768px) {
  .header-content {
    flex-wrap: wrap;
    gap: var(--space-4);
    padding: var(--space-4); /* Ensure padding on small screens */
  }
  
  .logo-text {
    font-size: var(--font-size-lg);
  }

  /* Make nav scrollable horizontally */
  .nav-links {
    order: 3;
    width: 100%;
    justify-content: flex-start; /* Align start to allow scroll from left */
    overflow-x: auto;
    white-space: nowrap;
    padding-bottom: var(--space-2); /* Space for scrollbar if visible */
    gap: var(--space-2);
    /* Hide scrollbar for cleaner look */
    -ms-overflow-style: none;  /* IE and Edge */
    scrollbar-width: none;  /* Firefox */
  }
  
  .nav-links::-webkit-scrollbar {
    display: none;
  }

  /* Hide divider on mobile to save space */
  .nav-divider {
    display: none;
  }

  .nav-link {
    background: var(--color-bg-secondary); /* Add bg to separate links visually */
    padding: var(--space-2) var(--space-3);
    font-size: var(--font-size-sm);
    flex-shrink: 0; /* Prevent shrinking */
  }
}
</style>
