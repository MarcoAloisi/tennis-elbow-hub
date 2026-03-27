<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import ThemeToggle from './components/common/ThemeToggle.vue'
import AdSidebar from './components/common/AdSidebar.vue'
import KofiWidget from './components/common/KofiWidget.vue'
import CookieConsent from './components/common/CookieConsent.vue'
import { useModalAccessibility } from './composables/useModalAccessibility'
import { Activity, BarChart2, Globe, Shirt, Clapperboard, LogOut, Database } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  authStore.initAuth()
})

const showAds = computed(() => {
  const noAdRoutes = ['/', '/privacy-policy', '/terms-of-service', '/contact']
  return !noAdRoutes.includes(route.path)
})

// Display name edit modal state
const showNameModal = ref(false)
const editName = ref('')
const nameError = ref('')

// Focus trap + Escape key for name modal
useModalAccessibility(showNameModal, {
  onClose: () => { showNameModal.value = false }
})

function openNameModal() {
  editName.value = authStore.user?.user_metadata?.display_name || authStore.user?.email?.split('@')[0] || ''
  nameError.value = ''
  showNameModal.value = true
}

async function submitNameChange() {
  if (!editName.value.trim()) return
  nameError.value = ''
  try {
    await authStore.updateDisplayName(editName.value.trim())
    showNameModal.value = false
  } catch (err) {
    nameError.value = err.message || 'Failed to update name.'
  }
}
</script>

<template>
  <div class="app-container">
    <!-- Skip to Content (Accessibility) -->
    <a href="#main-content" class="sr-only skip-link">Skip to main content</a>

    <!-- Header -->
    <header class="app-header">
      <div class="header-content">
        <RouterLink to="/" class="logo">
          <img src="/logo_fav.svg" alt="Tennis Elbow Hub" class="logo-image" />
          <span class="logo-text">Tennis Elbow Hub</span>
        </RouterLink>
        
        <nav class="nav-links" aria-label="Main navigation">
          <RouterLink to="/live" class="nav-link" active-class="active">
            <div class="icon-wrapper icon-live">
              <Activity class="nav-icon" :size="20" stroke-width="2.5" />
            </div>
            <span>Live Scores</span>
          </RouterLink>
          <div class="nav-divider"></div>
          <RouterLink to="/analysis" class="nav-link" active-class="active">
            <div class="icon-wrapper icon-analysis">
              <BarChart2 class="nav-icon" :size="20" stroke-width="2.5" />
            </div>
            <span>Match Log Analysis</span>
          </RouterLink>
          <div class="nav-divider"></div>
          <RouterLink to="/online-tours" class="nav-link" active-class="active">
            <div class="icon-wrapper icon-tours">
              <Globe class="nav-icon" :size="20" stroke-width="2.5" />
            </div>
            <span>Online Tours</span>
          </RouterLink>
          <div class="nav-divider"></div>
          <RouterLink to="/outfit-gallery" class="nav-link" active-class="active">
            <div class="icon-wrapper icon-gallery">
              <Shirt class="nav-icon" :size="20" stroke-width="2.5" />
            </div>
            <span>Outfit Gallery</span>
          </RouterLink>
          <div class="nav-divider"></div>
          <RouterLink to="/guides" class="nav-link" active-class="active">
            <div class="icon-wrapper icon-guides">
              <Clapperboard class="nav-icon" :size="20" stroke-width="2.5" />
            </div>
            <span>Guides</span>
          </RouterLink>
          <template v-if="authStore.isAdmin">
            <div class="nav-divider"></div>
            <RouterLink to="/admin/players" class="nav-link" active-class="active">
              <div class="icon-wrapper icon-admin">
                <Database class="nav-icon" :size="20" stroke-width="2.5" />
              </div>
              <span>Players DB</span>
            </RouterLink>
          </template>
        </nav>
        
        <div class="header-actions">
          <div class="nav-divider"></div>
          
          <div v-if="!authStore.loading" class="auth-buttons">
            <template v-if="authStore.user">
              <span 
                class="user-greeting is-clickable" 
                @click="openNameModal" 
                title="Click to set your Display Name"
              >
                Hi, {{ authStore.user?.user_metadata?.display_name || authStore.user?.email.split('@')[0] || 'Admin' }}
              </span>
              <button class="btn-logout" @click="authStore.logout()" title="Log Out" aria-label="Log out">
                <LogOut class="logout-icon" :size="18" />
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
      <main id="main-content" class="app-main">
        <RouterView />
      </main>

      <!-- Right Ad Rail -->
      <aside v-if="showAds" class="ad-rail right">
        <AdSidebar side="right" />
      </aside>
    </div>
    
    <!-- Cookie Consent Banner -->
    <CookieConsent />

    <!-- Ko-fi Widget -->
    <KofiWidget username="marcolinote4" />

    <!-- Display Name Edit Modal -->
    <div v-if="showNameModal" class="modal-overlay" @click.self="showNameModal = false" role="dialog" aria-modal="true" aria-label="Edit display name">
      <div class="name-modal">
        <h3><label for="display-name-input">Set Display Name</label></h3>
        <input 
          id="display-name-input"
          v-model="editName" 
          type="text" 
          placeholder="Enter your display name" 
          maxlength="50"
          @keyup.enter="submitNameChange"
          class="name-input"
        />
        <p v-if="nameError" class="name-error">{{ nameError }}</p>
        <div class="name-modal-actions">
          <button class="btn-modal-cancel" @click="showNameModal = false">Cancel</button>
          <button class="btn-modal-save" @click="submitNameChange" :disabled="!editName.trim()">Save</button>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <footer class="app-footer">
      <p>Tennis Elbow Hub &copy; 2026 — Tennis Elbow 4 Live Scores & Analysis</p>
      <div class="footer-links">
        <RouterLink to="/">About</RouterLink>
        <span class="footer-sep">·</span>
        <RouterLink to="/privacy-policy">Privacy Policy</RouterLink>
        <span class="footer-sep">·</span>
        <RouterLink to="/terms-of-service">Terms of Service</RouterLink>
        <span class="footer-sep">·</span>
        <RouterLink to="/contact">Contact</RouterLink>
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
  box-shadow: var(--shadow-md); /* Added shadow for lift */
  backdrop-filter: blur(10px);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
  max-width: 1200px; /* Reduced from 1400px for better focus */
  margin: 0 auto;
  padding: var(--space-4) var(--space-6);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
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
  min-height: 44px;
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
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
  box-shadow: inset 0 -2px 0 var(--color-brand-primary);
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  transition: all var(--transition-fast);
}

.nav-link:hover .icon-wrapper {
  transform: scale(1.1) rotate(5deg);
}

/* Icon specific colors (Neon logic) */
.icon-live {
  background: rgba(34, 197, 94, 0.15); /* Green */
  color: #22c55e;
}
.icon-analysis {
  background: rgba(168, 85, 247, 0.15); /* Purple */
  color: #a855f7;
}
.icon-tours {
  background: rgba(59, 130, 246, 0.15); /* Blue */
  color: #3b82f6;
}
.icon-gallery {
  background: rgba(236, 72, 153, 0.15); /* Pink */
  color: #ec4899;
}
.icon-guides {
  background: rgba(245, 158, 11, 0.15); /* Orange */
  color: #f59e0b;
}
.icon-admin {
  background: rgba(239, 68, 68, 0.15); /* Red */
  color: #ef4444;
}

[data-theme="dark"] .icon-live { color: #4ade80; }
[data-theme="dark"] .icon-analysis { color: #c084fc; }
[data-theme="dark"] .icon-tours { color: #60a5fa; }
[data-theme="dark"] .icon-gallery { color: #f472b6; }
[data-theme="dark"] .icon-guides { color: #fbbf24; }
[data-theme="dark"] .icon-admin { color: #f87171; }

.nav-icon {
  /* Removed global size here since controlled by wrapper */
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
  padding: var(--space-2) var(--space-4);
  min-height: 44px;
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
  width: 44px;
  height: 44px;
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
  background: var(--color-error-light);
  color: var(--color-error);
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
  z-index: var(--z-dropdown);
}

.footer-links {
  margin-top: var(--space-2);
  display: flex;
  justify-content: center;
  gap: var(--space-2);
}

.footer-links a {
  padding: var(--space-2);
  color: var(--color-text-muted);
  text-decoration: none;
  transition: color var(--transition-fast);
  min-height: 44px;
  display: inline-flex;
  align-items: center;
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

  /* Scroll fade indicator */
  .nav-links::after {
    content: '';
    position: sticky;
    right: 0;
    flex-shrink: 0;
    width: 32px;
    background: linear-gradient(to right, transparent, var(--color-surface));
    pointer-events: none;
  }

  /* Hide divider on mobile to save space */
  .nav-divider {
    display: none;
  }

  .nav-link {
    background: var(--color-bg-secondary);
    padding: var(--space-2) var(--space-3);
    font-size: var(--font-size-sm);
    flex-shrink: 0;
  }
}

/* Skip Link */
.skip-link:focus {
  position: fixed;
  top: var(--space-2);
  left: var(--space-2);
  z-index: var(--z-modal);
  padding: var(--space-3) var(--space-5);
  background: var(--color-accent);
  color: var(--color-text-inverse);
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-semibold);
  width: auto;
  height: auto;
  clip: auto;
  white-space: normal;
}

/* Display Name Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: var(--z-modal);
  padding: var(--space-4);
}

.name-modal {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  width: 100%;
  max-width: 400px;
  box-shadow: var(--shadow-xl);
}

.name-modal h3 {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

.name-input {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-family: inherit;
  margin-bottom: var(--space-3);
}

.name-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-light);
}

.name-error {
  color: var(--color-error);
  font-size: var(--font-size-sm);
  margin: 0 0 var(--space-3) 0;
}

.name-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.btn-modal-cancel {
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-fast);
}

.btn-modal-cancel:hover {
  color: var(--color-text-primary);
}

.btn-modal-save {
  padding: var(--space-2) var(--space-4);
  background: var(--color-brand-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: var(--font-weight-semibold);
  transition: all var(--transition-fast);
}

.btn-modal-save:hover:not(:disabled) {
  filter: brightness(1.1);
}

.btn-modal-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
