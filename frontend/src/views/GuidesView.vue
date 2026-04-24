<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useGuidesStore } from '@/stores/guides'
import { useAuthStore } from '@/stores/auth'
import GuideCard from '@/components/guides/GuideCard.vue'
import GuideFormModal from '@/components/guides/GuideFormModal.vue'
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import { usePagination } from '@/composables/usePagination'
import { useModalAccessibility } from '@/composables/useModalAccessibility'
import { Plus, Search, Video, BookOpen, BookMarked } from 'lucide-vue-next'

const guidesStore = useGuidesStore()
const authStore = useAuthStore()

// State
const selectedTag = ref('All')
const selectedType = ref('')
const isFormOpen = ref(false)
const editingGuide = ref(null)
const deleteConfirm = ref(null)

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

function fetchFiltered(overrides = {}) {
  guidesStore.fetchGuides({
    tag: selectedTag.value,
    type: selectedType.value,
    search: searchQuery.value,
    page: 1,
    pageSize: 12,
    ...overrides
  })
}

onMounted(() => {
  guidesStore.fetchGuides()
  guidesStore.fetchTags()
})

// Live search with debounce (replaces manual setTimeout pattern)
const { searchQuery } = useDebouncedSearch((query) => {
  fetchFiltered({ search: query })
})

function setTag(tag) {
  selectedTag.value = tag
  fetchFiltered({ tag })
}

function setType(type) {
  selectedType.value = type
  fetchFiltered({ type })
}

// Pagination (replaces manual pageNumbers + goToPage)
const { pageNumbers, goToPage } = usePagination({
  currentPage: () => guidesStore.pagination.page,
  totalPages: () => guidesStore.pagination.totalPages,
  totalItems: () => guidesStore.pagination.total || 0,
  pageSize: 12,
  onPageChange: (page) => fetchFiltered({ page })
})

// Focus trap + Escape for delete modal
const deleteModalOpen = computed(() => !!deleteConfirm.value)
useModalAccessibility(deleteModalOpen, {
  onClose: () => { deleteConfirm.value = null }
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
      <button v-if="authStore.isAdmin" class="btn btn-primary" @click="openAddForm">
        <Plus :size="15" stroke-width="2.5" /> Add Guide
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
          <button class="type-btn mod-video" :class="{ active: selectedType === 'video' }" @click="setType('video')">
            Video
          </button>
          <button class="type-btn mod-article" :class="{ active: selectedType === 'written' }" @click="setType('written')">
            Article
          </button>
        </div>

        <div class="search-bar-wrapper">
          <span class="search-bar-icon"><Search :size="18" /></span>
          <input
            type="text"
            v-model="searchQuery"
            placeholder="Search guides..."
            class="search-bar-input"
          />
          <button v-if="searchQuery" class="search-bar-clear" @click="searchQuery = ''" title="Clear search" aria-label="Clear search">✕</button>
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
    <div v-else class="empty-state-dashed">
      <div v-if="guidesStore.loading" class="loading-spinner-lg"></div>
      <div v-else class="no-results">
        <div class="empty-icon-wrapper">
          <BookMarked class="empty-icon" :size="48" :stroke-width="1.5" />
        </div>
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
          aria-label="Previous page"
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
          aria-label="Next page"
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
    <div v-if="deleteConfirm" class="modal-overlay" @click.self="deleteConfirm = null" role="dialog" aria-modal="true" aria-label="Delete guide confirmation">
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

/* Buttons — uses global .btn-primary from components.css */

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

.mod-video:not(.active) .btn-icon-left {
  color: #ef4444; /* red */
}
.mod-article:not(.active) .btn-icon-left {
  color: #3b82f6; /* blue */
}

/* Search Bar styling */
.search-bar-wrapper {
  position: relative;
  flex: 1;
}

.search-bar-icon {
  position: absolute;
  top: 50%;
  left: 12px;
  transform: translateY(-50%);
  color: var(--color-text-muted);
  pointer-events: none;
}

.search-bar-input {
  width: 100%;
  padding-left: 40px;
}

.empty-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(34, 197, 94, 0.1); 
  color: #22c55e;
  margin: 0 auto var(--space-4);
  box-shadow: 0 0 20px rgba(34, 197, 94, 0.2);
}

[data-theme="dark"] .empty-icon-wrapper {
  color: #4ade80;
  background: rgba(74, 222, 128, 0.1);
  box-shadow: 0 0 20px rgba(74, 222, 128, 0.15);
}

/* Grid */
.guides-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-6);
}



/* Pagination — uses global classes from components.css */

/* Delete confirmation modal — uses global .modal-overlay from components.css */
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
  z-index: var(--z-modal);
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
  background: var(--color-error);
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-inverse);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-danger:hover {
  filter: brightness(0.9);
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
