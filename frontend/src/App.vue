<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { useHead } from '@unhead/vue'
type ElWithHandler = HTMLElement & { _clickOutsideHandler?: (e: MouseEvent) => void }
const vClickOutside = {
  mounted(el: ElWithHandler, binding: { value: () => void }) {
    el._clickOutsideHandler = (event: MouseEvent) => {
      if (!event.composedPath().includes(el)) binding.value()
    }
    document.addEventListener('click', el._clickOutsideHandler)
  },
  unmounted(el: ElWithHandler) {
    if (el._clickOutsideHandler) {
      document.removeEventListener('click', el._clickOutsideHandler)
    }
  },
}
import { useAuthStore } from './stores/auth'
import { usePresenceStore } from './stores/presence'
import ThemeToggle from './components/common/ThemeToggle.vue'
import TourPromo from './components/common/TourPromo.vue'
import KofiWidget from './components/common/KofiWidget.vue'
import CookieConsent from './components/common/CookieConsent.vue'
import InstagramCTA from './components/common/InstagramCTA.vue'
import { useModalAccessibility } from './composables/useModalAccessibility'
import { LogOut, Database, Shield, ChevronDown, User, Menu, X } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

// Per-route title/description, baked into the prerendered HTML for each
// route (replaces the old document.title mutation in a router guard, which
// only ever ran after client-side hydration and left every prerendered page
// with the same static <head> from index.html).
const SITE_URL = 'https://tenniselbowhub.live'

useHead({
  title: () => `${(route.meta.title as string) || 'Tennis Elbow Hub'} | Tennis Elbow Hub`,
  link: [
    { rel: 'canonical', href: () => `${SITE_URL}${route.path}` },
  ],
  meta: [
    {
      name: 'description',
      content: () => (route.meta.description as string) || 'Tennis Elbow Hub - Live scores and match analysis for Tennis Elbow 4',
    },
    {
      property: 'og:title',
      content: () => `${(route.meta.title as string) || 'Tennis Elbow Hub'} | Tennis Elbow Hub`,
    },
    {
      property: 'og:description',
      content: () => (route.meta.description as string) || 'Tennis Elbow Hub - Live scores and match analysis for Tennis Elbow 4',
    },
    { property: 'og:url', content: () => `${SITE_URL}${route.path}` },
    { property: 'og:image', content: `${SITE_URL}/logo.png` },
    { property: 'og:type', content: 'website' },
    { name: 'twitter:card', content: 'summary' },
  ],
})

const authStore = useAuthStore()
const presenceStore = usePresenceStore()

onMounted(() => {
  authStore.initAuth()
})

const showBanners = computed(
  () => route.path === '/live' || route.path.startsWith('/online-tours'),
)

const showUserMenu = ref(false)
const showMobileMenu = ref(false)

watch(() => route.fullPath, () => { showMobileMenu.value = false })

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
          <img src="/logo_fav.svg" alt="" width="28" height="28" class="logo-image" />
          <span class="logo-text">Tennis Elbow Hub</span>
        </RouterLink>

        <nav class="nav-links" aria-label="Main navigation">
          <RouterLink to="/live" class="nav-link" active-class="active">Live scores</RouterLink>
          <RouterLink to="/analysis" class="nav-link" active-class="active">Match analysis</RouterLink>
          <RouterLink to="/online-tours" class="nav-link" active-class="active">Online tours</RouterLink>
          <RouterLink to="/outfit-gallery" class="nav-link" active-class="active">Outfits</RouterLink>
          <RouterLink to="/guides" class="nav-link" active-class="active">Guides</RouterLink>
          <RouterLink v-if="authStore.isAdmin" to="/admin/players" class="nav-link" active-class="active">Players DB</RouterLink>
        </nav>

        <div class="header-actions">
          <div v-if="!authStore.loading" class="auth-buttons">
            <template v-if="authStore.user">
              <div class="user-menu-wrapper" v-click-outside="() => { showUserMenu = false }">
                <button
                  type="button"
                  class="user-greeting"
                  :aria-expanded="showUserMenu"
                  @click="showUserMenu = !showUserMenu"
                >
                  {{ authStore.user?.user_metadata?.display_name || authStore.user?.email.split('@')[0] || 'Admin' }}
                  <ChevronDown :size="14" class="menu-chevron" :class="{ rotated: showUserMenu }" />
                </button>
                <div v-if="showUserMenu" class="user-dropdown" @click="showUserMenu = false">
                  <RouterLink to="/profile" class="dropdown-item">
                    <User :size="15" /> My profile
                  </RouterLink>
                  <template v-if="authStore.isAdmin">
                    <div class="dropdown-divider"></div>
                    <RouterLink to="/admin/players" class="dropdown-item">
                      <Database :size="15" /> Players DB
                    </RouterLink>
                    <RouterLink to="/admin/panel" class="dropdown-item">
                      <Shield :size="15" /> Admin panel
                    </RouterLink>
                    <RouterLink to="/admin/users" class="dropdown-item">
                      <User :size="15" /> Registered users
                    </RouterLink>
                  </template>
                </div>
              </div>
              <button class="btn-logout" @click="authStore.logout()" title="Log out" aria-label="Log out">
                <LogOut class="logout-icon" :size="18" />
              </button>
            </template>
            <template v-else>
              <button class="btn-login" @click="router.push('/login')">Log in</button>
            </template>
          </div>
          <ThemeToggle />

          <div class="mobile-menu" v-click-outside="() => { showMobileMenu = false }">
            <button
              type="button"
              class="mobile-menu-toggle"
              :aria-expanded="showMobileMenu"
              aria-controls="mobile-menu-panel"
              :aria-label="showMobileMenu ? 'Close menu' : 'Open menu'"
              @click="showMobileMenu = !showMobileMenu"
            >
              <X v-if="showMobileMenu" :size="20" />
              <Menu v-else :size="20" />
            </button>
            <nav v-if="showMobileMenu" id="mobile-menu-panel" class="mobile-menu-panel" aria-label="Menu">
              <RouterLink to="/live" class="mobile-link" active-class="active">Live scores</RouterLink>
              <RouterLink to="/analysis" class="mobile-link" active-class="active">Match analysis</RouterLink>
              <RouterLink to="/online-tours" class="mobile-link" active-class="active">Online tours</RouterLink>
              <RouterLink to="/outfit-gallery" class="mobile-link" active-class="active">Outfits</RouterLink>
              <RouterLink to="/guides" class="mobile-link" active-class="active">Guides</RouterLink>
              <template v-if="authStore.user">
                <RouterLink to="/profile" class="mobile-link" active-class="active">My profile</RouterLink>
                <template v-if="authStore.isAdmin">
                  <RouterLink to="/admin/players" class="mobile-link" active-class="active">Players DB</RouterLink>
                  <RouterLink to="/admin/panel" class="mobile-link" active-class="active">Admin panel</RouterLink>
                  <RouterLink to="/admin/users" class="mobile-link" active-class="active">Registered users</RouterLink>
                </template>
                <button type="button" class="mobile-link" @click="authStore.logout()">Log out</button>
              </template>
              <RouterLink v-else to="/login" class="mobile-link">Log in</RouterLink>
            </nav>
          </div>
        </div>
      </div>
    </header>

    <!-- Content Wrapper with Ads -->
    <div class="content-wrapper">
      <aside v-if="showBanners" class="side-rail left">
        <TourPromo tour="xkt" href="https://xkt-tour.com/" label="Visit xkt-tour.com" />
      </aside>

      <!-- Main Content -->
      <main id="main-content" class="app-main">
        <RouterView />
      </main>

      <aside v-if="showBanners" class="side-rail right">
        <TourPromo tour="wtsl" href="https://www.wtslforum.com/" label="Visit wtslforum.com" />
      </aside>
    </div>
    
    <!-- Cookie Consent Banner -->
    <CookieConsent />

    <!-- Ko-fi Widget -->
    <KofiWidget username="marcolinote4" />

    <!-- Instagram CTA -->
    <InstagramCTA />

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
      <div class="footer-inner">
        <div class="footer-meta">
          <p>Tennis Elbow Hub &copy; 2026. Live scores and match analysis for Tennis Elbow 4.</p>
          <p v-if="presenceStore.isConnected" class="footer-presence">{{ presenceStore.registeredCount }} members and {{ presenceStore.guestCount }} guests online</p>
        </div>
        <div class="footer-links">
          <RouterLink to="/about">About</RouterLink>
          <RouterLink to="/privacy-policy">Privacy Policy</RouterLink>
          <RouterLink to="/terms-of-service">Terms of Service</RouterLink>
          <RouterLink to="/contact">Contact</RouterLink>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  background: var(--color-surface);
}

.header-content {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  max-width: 1248px;
  height: 60px;
  margin: 0 auto;
  padding: 0 var(--space-6);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  white-space: nowrap;
}

.logo-image {
  height: 28px;
  width: auto;
}

.logo-text {
  font-family: var(--font-heading);
  font-size: 1.2rem;
  font-weight: 800;
  letter-spacing: -0.01em;
  color: var(--color-text-primary);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
}

.nav-link {
  display: flex;
  align-items: center;
  padding: 0 var(--space-4);
  min-height: 40px;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  font-size: 0.9375rem;
  white-space: nowrap;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.nav-link:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

.nav-link.active {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  margin-left: auto;
}

.auth-buttons {
  display: flex;
  align-items: center;
}

.user-greeting {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: 40px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.user-greeting:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

.user-menu-wrapper {
  position: relative;
}

.menu-chevron {
  transition: transform var(--transition-fast);
}

.menu-chevron.rotated {
  transform: rotate(180deg);
}

.user-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  min-width: 180px;
  padding: var(--space-1);
  z-index: var(--z-dropdown);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-3);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  white-space: nowrap;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.dropdown-item:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.dropdown-divider {
  height: var(--space-1);
}

.btn-login {
  display: flex;
  align-items: center;
  min-height: 40px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  font-size: 0.9375rem;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.btn-login:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

.btn-logout {
  background: transparent;
  color: var(--color-text-secondary);
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.btn-logout:hover {
  background: var(--color-error-light);
  color: var(--color-error);
}

.mobile-menu {
  display: none;
  position: relative;
}

.mobile-menu-toggle {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
}

.mobile-menu-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  width: 240px;
  display: grid;
  padding: var(--space-1);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  z-index: var(--z-dropdown);
}

.mobile-link {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  text-align: left;
  cursor: pointer;
}

.mobile-link:hover,
.mobile-link.active {
  color: var(--color-text-primary);
  background: var(--color-bg-tertiary);
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
  max-width: 1248px;
  padding: var(--space-6) var(--space-6) var(--space-16);
  /* Removed margin: 0 auto as flex handles centering/layout */
}

/* Ad Rails */
.side-rail {
  display: none; /* Hidden by default */
  width: 200px; /* Base width for rail */
  padding-top: var(--space-8);
}

/* Responsive Ads: Show only on large screens */
@media (min-width: 1600px) {
  .side-rail {
    display: flex;
  }

  .side-rail.left {
    justify-content: flex-end;
    padding-right: var(--space-4);
  }

  .side-rail.right {
    justify-content: flex-start;
    padding-left: var(--space-4);
  }
}

.app-footer {
  margin-top: var(--space-8);
  background: var(--color-surface);
  padding: var(--space-8) var(--space-6) calc(var(--space-16) + var(--space-4));
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  position: relative;
  z-index: var(--z-dropdown);
}

.footer-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2) var(--space-8);
}

.app-footer p {
  color: inherit;
}

.footer-presence {
  margin-top: var(--space-1);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.footer-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0 var(--space-6);
}

.footer-links a {
  color: var(--color-text-secondary);
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  transition: color var(--transition-fast);
}

.footer-links a:hover {
  color: var(--color-text-primary);
}

/* Responsive */
@media (max-width: 900px) {
  .nav-links,
  .auth-buttons {
    display: none;
  }

  .mobile-menu {
    display: block;
  }
}

@media (max-width: 768px) {
  .header-content {
    height: 56px;
    padding: 0 var(--space-4);
    gap: var(--space-3);
  }

  .app-main {
    padding: var(--space-4);
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
