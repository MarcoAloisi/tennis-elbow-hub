<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useGuidesStore } from '@/stores/guides'
import { useAuthStore } from '@/stores/auth'
import GuideCard from '@/components/guides/GuideCard.vue'
import GuideFormModal from '@/components/guides/GuideFormModal.vue'

const guidesStore = useGuidesStore()
const authStore = useAuthStore()

// State
const selectedTag = ref('All')
const selectedType = ref('')
const searchQuery = ref('')
const isFormOpen = ref(false)
const editingGuide = ref(null)
const deleteConfirm = ref(null)

let searchTimer = null

// Computed filter tags: "All" + tags from API
const filterTags = computed(() => {
  return ['All', ...guidesStore.tags]
})

// Fetch helpers
function fetchCurrentPage() {
  guidesStore.fetchGuides({
    tag: selectedTag.value,
    type: selectedType.value,
    search: searchQuery.value,
    page: guidesStore.pagination.page,
    pageSize: 12
  })
}

onMounted(() => {
  guidesStore.fetchGuides()
  guidesStore.fetchTags()
})

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})

// Live search with debounce
watch(searchQuery, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    guidesStore.fetchGuides({
      tag: selectedTag.value,
      type: selectedType.value,
      search: searchQuery.value,
      page: 1,
      pageSize: 12
    })
  }, 300)
})

function setTag(tag) {
  selectedTag.value = tag
  guidesStore.fetchGuides({
    tag,
    type: selectedType.value,
    search: searchQuery.value,
    page: 1,
    pageSize: 12
  })
}

function setType(type) {
  selectedType.value = type
  guidesStore.fetchGuides({
    tag: selectedTag.value,
    type,
    search: searchQuery.value,
    page: 1,
    pageSize: 12
  })
}

function goToPage(page) {
  if (page < 1 || page > guidesStore.pagination.totalPages) return
  guidesStore.fetchGuides({
    tag: selectedTag.value,
    type: selectedType.value,
    search: searchQuery.value,
    page,
    pageSize: 12
  })
}

// Pagination display
const pageNumbers = computed(() => {
  const total = guidesStore.pagination.totalPages
  const current = guidesStore.pagination.page
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages = [1]
  if (current > 3) pages.push('...')
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  if (current < total - 2) pages.push('...')
  pages.push(total)
  return pages
})

// Admin actions
function openAddForm() {
  editingGuide.value = null
  isFormOpen.value = true
}

function handleEdit(guide) {
  editingGuide.value = guide
  isFormOpen.value = true
}

async function handleDelete(guide) {
  deleteConfirm.value = guide
}

async function confirmDelete() {
  if (!deleteConfirm.value) return
  try {
    const token = authStore.session?.access_token
    await guidesStore.deleteGuide(deleteConfirm.value.id, token)
    deleteConfirm.value = null
    fetchCurrentPage()
  } catch (err) {
    console.error('Delete failed:', err)
  }
}

function onFormSaved() {
  fetchCurrentPage()
  guidesStore.fetchTags()
}
</script>

<template>
  <div class="guides-view">
    <!-- Header -->
    <header class="guides-header">
      <div>
        <h1>Guides</h1>
        <p class="subtitle">Tutorials and articles to help you master Tennis Elbow 4.</p>
      </div>
      <button v-if="authStore.user" class="btn-primary" @click="openAddForm">
        <span class="icon">➕</span> Add Guide
      </button>
    </header>

    <!-- Filters -->
    <div class="filters-section">
      <!-- Tag Filters -->
      <div class="tag-filters">
        <button
          v-for="tag in filterTags"
          :key="tag"
          class="tag-btn"
          :class="{ active: selectedTag === tag }"
          @click="setTag(tag)"
        >
          {{ tag }}
        </button>
      </div>

      <!-- Type + Search Row -->
      <div class="filter-row">
        <div class="type-filter">
          <button class="type-btn" :class="{ active: selectedType === '' }" @click="setType('')">All</button>
          <button class="type-btn" :class="{ active: selectedType === 'video' }" @click="setType('video')">📹 Video</button>
          <button class="type-btn" :class="{ active: selectedType === 'written' }" @click="setType('written')">📖 Article</button>
        </div>

        <div class="search-wrapper">
          <span class="search-icon">🔍</span>
          <input
            type="text"
            v-model="searchQuery"
            placeholder="Search guides..."
            class="search-input"
          />
          <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''" title="Clear search">✕</button>
        </div>
      </div>
    </div>

    <!-- Guides Grid -->
    <div class="guides-grid" v-if="guidesStore.guides.length > 0">
      <GuideCard
        v-for="guide in guidesStore.guides"
        :key="guide.id"
        :guide="guide"
        @edit="handleEdit"
        @delete="handleDelete"
      />
    </div>

    <!-- Empty / Loading State -->
    <div v-else class="empty-state">
      <div v-if="guidesStore.loading" class="loading-spinner"></div>
      <div v-else class="no-results">
        <div class="empty-icon">📚</div>
        <h3>No guides found</h3>
        <p v-if="searchQuery || selectedTag !== 'All' || selectedType">Try adjusting your search or filters.</p>
        <p v-else>No guides available yet.</p>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="guidesStore.pagination.totalPages > 1" class="pagination-container">
      <div class="pagination-controls">
        <button
          class="page-btn nav-btn"
          :disabled="guidesStore.pagination.page <= 1"
          @click="goToPage(guidesStore.pagination.page - 1)"
          title="Previous page"
        >
          ‹
        </button>
        <template v-for="(p, idx) in pageNumbers" :key="idx">
          <span v-if="p === '...'" class="page-ellipsis">…</span>
          <button
            v-else
            class="page-btn"
            :class="{ active: p === guidesStore.pagination.page }"
            @click="goToPage(p)"
          >
            {{ p }}
          </button>
        </template>
        <button
          class="page-btn nav-btn"
          :disabled="guidesStore.pagination.page >= guidesStore.pagination.totalPages"
          @click="goToPage(guidesStore.pagination.page + 1)"
          title="Next page"
        >
          ›
        </button>
      </div>
    </div>

    <!-- Guide Form Modal -->
    <GuideFormModal
      :visible="isFormOpen"
      :editGuide="editingGuide"
      @close="isFormOpen = false; editingGuide = null"
      @saved="onFormSaved"
    />

    <!-- Delete Confirmation Modal -->
    <div v-if="deleteConfirm" class="modal-overlay" @click.self="deleteConfirm = null">
      <div class="delete-modal">
        <h3>Delete Guide</h3>
        <p>Are you sure you want to delete <strong>"{{ deleteConfirm.title }}"</strong>? This action cannot be undone.</p>
        <div class="delete-actions">
          <button class="btn-cancel" @click="deleteConfirm = null">Cancel</button>
          <button class="btn-danger" @click="confirmDelete">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.guides-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
  min-height: 100%;
}

/* Header */
.guides-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
  flex-wrap: wrap;
  gap: var(--space-4);
}

.guides-header h1 {
  font-family: var(--font-heading);
  font-size: var(--font-size-3xl);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2) 0;
}

.subtitle {
  color: var(--color-text-secondary);
  font-size: var(--font-size-lg);
  margin: 0;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 10px 20px;
  background: var(--color-brand-primary);
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-inverse);
  cursor: pointer;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: var(--font-size-sm);
  transition: all 0.2s ease;
}

.btn-primary:hover {
  filter: brightness(1.1);
  box-shadow: 0 2px 8px rgba(163, 230, 53, 0.3);
}

/* Filters */
.filters-section {
  margin-bottom: var(--space-6);
}

.tag-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.tag-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tag-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.tag-btn.active {
  background: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
  color: var(--color-text-inverse);
}

.filter-row {
  display: flex;
  gap: var(--space-3);
  align-items: stretch;
  flex-wrap: wrap;
}

.type-filter {
  display: flex;
  background: var(--color-bg-secondary);
  padding: 3px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
}

.type-btn {
  padding: 6px 16px;
  border-radius: var(--radius-full);
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-weight: 600;
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.type-btn.active {
  background: var(--color-brand-primary);
  color: var(--color-text-inverse);
  box-shadow: var(--shadow-sm);
}

.type-btn:hover:not(.active) {
  color: var(--color-text-primary);
}

.search-wrapper {
  flex: 1;
  min-width: 200px;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 14px;
  font-size: var(--font-size-base);
  pointer-events: none;
  z-index: 1;
}

.search-input {
  width: 100%;
  padding: 10px 36px 10px 40px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: var(--font-size-base);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.search-input:focus {
  outline: none;
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 3px rgba(163, 230, 53, 0.15);
}

.search-input::placeholder {
  color: var(--color-text-muted);
}

.clear-btn {
  position: absolute;
  right: 10px;
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: var(--font-size-sm);
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}

.clear-btn:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

/* Grid */
.guides-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-6);
}

/* Empty State */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px dashed var(--color-border);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-brand-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.no-results {
  text-align: center;
  color: var(--color-text-secondary);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: var(--space-4);
  opacity: 0.5;
}

.no-results h3 {
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

/* Pagination */
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--color-border);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-btn {
  min-width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: var(--font-heading);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.page-btn:hover:not(:disabled):not(.active) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  border-color: var(--color-brand-primary);
}

.page-btn.active {
  background: var(--color-brand-primary);
  color: var(--color-text-inverse);
  border-color: var(--color-brand-primary);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.nav-btn {
  font-size: var(--font-size-lg);
  font-weight: 700;
}

.page-ellipsis {
  min-width: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  user-select: none;
}

/* Delete confirmation modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: var(--space-4);
}

.delete-modal {
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  max-width: 420px;
  width: 100%;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-xl);
}

.delete-modal h3 {
  margin: 0 0 var(--space-3) 0;
  color: var(--color-text-primary);
  font-family: var(--font-heading);
}

.delete-modal p {
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-4) 0;
}

.delete-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.btn-cancel {
  padding: 8px 16px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-weight: 600;
}

.btn-cancel:hover {
  color: var(--color-text-primary);
}

.btn-danger {
  padding: 8px 16px;
  background: #ef4444;
  border: none;
  border-radius: var(--radius-md);
  color: white;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-danger:hover {
  background: #dc2626;
}

/* Responsive */
@media (max-width: 640px) {
  .guides-grid {
    grid-template-columns: 1fr;
  }

  .filter-row {
    flex-direction: column;
  }

  .tag-filters {
    justify-content: center;
  }
}
</style>
