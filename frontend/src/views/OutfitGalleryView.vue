<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useOutfitsStore } from '@/stores/outfits'
import { useAuthStore } from '@/stores/auth'
import OutfitCard from '@/components/outfits/OutfitCard.vue'

const outfitsStore = useOutfitsStore()
const authStore = useAuthStore()

// State
const isUploadModalOpen = ref(false)
const selectedCategory = ref('All')
const searchQuery = ref('')
const selectedUploader = ref('')
const categories = ['All', 'Male', 'Female']

// Debounce timer for search
let searchTimer = null

// Form State
const formModel = ref({
  title: '',
  outfit_code: '',
  category: 'Male',
  uploader_name: '',
  image: null
})
const fileInput = ref(null)
const uploadError = ref('')
const uploadSuccess = ref(false)
const isSubmitting = ref(false)
const editingOutfitId = ref(null)

const handleEditOutfit = (outfit) => {
  editingOutfitId.value = outfit.id
  formModel.value = {
    title: outfit.title,
    outfit_code: outfit.outfit_code,
    category: outfit.category,
    uploader_name: outfit.uploader_name,
    image: null // Optional during edit
  }
  isUploadModalOpen.value = true
  uploadSuccess.value = false
  uploadError.value = ''
}

// Fetch data helper
const fetchCurrentPage = () => {
  outfitsStore.fetchOutfits({
    search: searchQuery.value,
    uploader: selectedUploader.value,
    category: selectedCategory.value,
    page: outfitsStore.pagination.page,
    pageSize: 9
  })
}

onMounted(() => {
  outfitsStore.fetchOutfits()
  outfitsStore.fetchUploaders()
  window.addEventListener('paste', handlePaste)
})

onUnmounted(() => {
  window.removeEventListener('paste', handlePaste)
  if (searchTimer) clearTimeout(searchTimer)
})

// Live search with debounce
watch(searchQuery, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    outfitsStore.fetchOutfits({
      search: searchQuery.value,
      uploader: selectedUploader.value,
      category: selectedCategory.value,
      page: 1,
      pageSize: 9
    })
  }, 300)
})

const setCategory = (cat) => {
  selectedCategory.value = cat
  outfitsStore.fetchOutfits({
    search: searchQuery.value,
    uploader: selectedUploader.value,
    category: cat,
    page: 1,
    pageSize: 9
  })
}

const onUploaderChange = () => {
  outfitsStore.fetchOutfits({
    search: searchQuery.value,
    uploader: selectedUploader.value,
    category: selectedCategory.value,
    page: 1,
    pageSize: 9
  })
}

const goToPage = (page) => {
  if (page < 1 || page > outfitsStore.pagination.totalPages) return
  outfitsStore.fetchOutfits({
    search: searchQuery.value,
    uploader: selectedUploader.value,
    category: selectedCategory.value,
    page,
    pageSize: 9
  })
}

// Pagination display helper — shows smart page range with ellipsis
const pageNumbers = computed(() => {
  const total = outfitsStore.pagination.totalPages
  const current = outfitsStore.pagination.page
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  const pages = []
  pages.push(1)
  if (current > 3) pages.push('...')
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  if (current < total - 2) pages.push('...')
  pages.push(total)
  return pages
})

const showingRange = computed(() => {
  const { page, pageSize, total } = outfitsStore.pagination
  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)
  return { from, to, total }
})

const handleFileChange = (e) => {
  const file = e.dataTransfer ? e.dataTransfer.files[0] : e.target.files[0]
  if (file) {
    if (!file.type.startsWith('image/')) {
      uploadError.value = 'Please upload a valid image file.'
      if (fileInput.value) fileInput.value.value = ''
      dragActive.value = false
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      uploadError.value = 'File size must be less than 5MB.'
      if (fileInput.value) fileInput.value.value = ''
      dragActive.value = false
      return
    }
    formModel.value.image = file
    uploadError.value = ''
    dragActive.value = false
  }
}

const removeImage = (e) => {
  e.stopPropagation()
  formModel.value.image = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const dragActive = ref(false)
const onDragOver = () => { dragActive.value = true }
const onDragLeave = () => { dragActive.value = false }
const onDrop = (e) => { handleFileChange(e) }

const handlePaste = (e) => {
  if (e.target.tagName === 'INPUT' && e.target.type !== 'file') return
  if (e.target.tagName === 'TEXTAREA') return
  if (e.clipboardData && e.clipboardData.files && e.clipboardData.files.length > 0) {
    e.preventDefault()
    handleFileChange({ target: { files: e.clipboardData.files } })
  }
}

const submitForm = async () => {
  uploadError.value = ''
  uploadSuccess.value = false
  
  if (!editingOutfitId.value && !formModel.value.image) {
    uploadError.value = 'Please select an image to upload.'
    return
  }
  
  isSubmitting.value = true
  
  try {
    const formData = new FormData()
    formData.append('title', formModel.value.title)
    formData.append('outfit_code', formModel.value.outfit_code)
    formData.append('category', formModel.value.category)
    formData.append('uploader_name', formModel.value.uploader_name || authStore.user?.user_metadata?.display_name || 'Anonymous')
    if (formModel.value.image) {
      formData.append('image', formModel.value.image)
    }
    
    const token = authStore.session?.access_token
    if (editingOutfitId.value) {
      await outfitsStore.updateOutfit(editingOutfitId.value, formData, token)
    } else {
      await outfitsStore.createOutfit(formData, token)
    }
    
    uploadSuccess.value = true
    setTimeout(() => {
      closeUploadModal()
      // Re-fetch current page to reflect changes
      fetchCurrentPage()
    }, 1500)
    
  } catch (err) {
    uploadError.value = err.message || (editingOutfitId.value ? 'Failed to update outfit.' : 'Failed to upload outfit.')
  } finally {
    isSubmitting.value = false
  }
}

const openUploadModal = () => {
  isUploadModalOpen.value = true
  uploadSuccess.value = false
  uploadError.value = ''
}

const closeUploadModal = () => {
  isUploadModalOpen.value = false
  dragActive.value = false
  editingOutfitId.value = null
  formModel.value = {
    title: '',
    outfit_code: '',
    category: 'Male',
    uploader_name: '',
    image: null
  }
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

</script>

<template>
  <div class="gallery-view">
    <header class="gallery-header">
      <div>
        <h1>Outfit Code Gallery</h1>
        <p class="subtitle">Browse, preview, and copy player outfits for Tennis Elbow 4.</p>
      </div>
      
      <!-- Upload Button (Only for logged-in users) -->
      <button v-if="authStore.isAdmin" class="btn-primary" @click="openUploadModal">
        <span class="icon">➕</span> Upload Outfit
      </button>
    </header>

    <!-- Filters -->
    <div class="filters-container">
      <div class="category-tabs">
        <button 
          v-for="cat in categories" 
          :key="cat"
          class="tab-btn"
          :class="{ active: selectedCategory === cat }"
          @click="setCategory(cat)"
        >
          {{ cat }}
        </button>
      </div>
    </div>

    <!-- Search & Author Filter Bar -->
    <div class="search-filter-bar">
      <div class="search-input-wrapper">
        <span class="search-icon">🔍</span>
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="Search outfits by name..." 
          class="search-input"
        />
        <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''" title="Clear search">✕</button>
      </div>
      <div class="uploader-filter-wrapper">
        <select v-model="selectedUploader" @change="onUploaderChange" class="uploader-select">
          <option value="">All Authors</option>
          <option v-for="name in outfitsStore.uploaders" :key="name" :value="name">
            {{ name }}
          </option>
        </select>
      </div>
    </div>

    <!-- Gallery Grid -->
    <div class="gallery-grid" v-if="outfitsStore.outfits.length > 0">
      <div v-for="outfit in outfitsStore.outfits" :key="outfit.id" class="grid-item">
        <OutfitCard :outfit="outfit" @edit="handleEditOutfit" />
      </div>
    </div>
    
    <!-- Empty State / Loading -->
    <div v-else class="empty-state">
      <div v-if="outfitsStore.loading" class="loading-spinner"></div>
      <div v-else class="no-results">
        <div class="icon">👕</div>
        <h3>No outfits found</h3>
        <p v-if="searchQuery || selectedUploader">Try adjusting your search or filters.</p>
        <p v-else>There are currently no outfits uploaded for this category.</p>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="outfitsStore.pagination.totalPages > 1" class="pagination-container">
      <span class="pagination-info">
        Showing {{ showingRange.from }}–{{ showingRange.to }} of {{ showingRange.total }}
      </span>
      <div class="pagination-controls">
        <button 
          class="page-btn nav-btn" 
          :disabled="outfitsStore.pagination.page <= 1"
          @click="goToPage(outfitsStore.pagination.page - 1)"
          title="Previous page"
        >
          ‹
        </button>
        <template v-for="(p, idx) in pageNumbers" :key="idx">
          <span v-if="p === '...'" class="page-ellipsis">…</span>
          <button 
            v-else 
            class="page-btn"
            :class="{ active: p === outfitsStore.pagination.page }"
            @click="goToPage(p)"
          >
            {{ p }}
          </button>
        </template>
        <button 
          class="page-btn nav-btn" 
          :disabled="outfitsStore.pagination.page >= outfitsStore.pagination.totalPages"
          @click="goToPage(outfitsStore.pagination.page + 1)"
          title="Next page"
        >
          ›
        </button>
      </div>
    </div>

    <!-- Upload Modal -->
    <div v-if="isUploadModalOpen" class="modal-overlay" @click.self="closeUploadModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ editingOutfitId ? 'Edit Outfit' : 'Upload New Outfit' }}</h2>
          <button class="btn-close" @click="closeUploadModal">✕</button>
        </div>
        
        <form @submit.prevent="submitForm" class="upload-form">
          <div class="form-group">
            <label for="title">Outfit Title</label>
            <input id="title" v-model="formModel.title" required placeholder="e.g. Sinner US Open 2024" />
          </div>
          
          <div class="form-row">
            <div class="form-group w-50">
              <label for="category">Category</label>
              <select id="category" v-model="formModel.category" required>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
              </select>
            </div>
            
            <div class="form-group w-50">
              <label for="uploader">Your Name (Optional)</label>
              <input id="uploader" v-model="formModel.uploader_name" placeholder="Leave blank to use auth name" />
            </div>
          </div>
          
          <div class="form-group">
            <label for="outfitCode">Outfit Code</label>
            <textarea 
              id="outfitCode" 
              v-model="formModel.outfit_code" 
              required 
              rows="4" 
              placeholder='OutfitTE4		=	v2 Eb n0 ; Cr s0 n05 ; Cl s0 n05 ; Ht ; G n0 ...'
            ></textarea>
            <small class="hint">The full code generated by the game.</small>
          </div>
          
          <div class="form-group">
            <label>Outfit Picture (PNG/JPG)</label>
            <div 
              class="drop-zone" 
              :class="{ 'is-dragover': dragActive }"
              @dragover.prevent="onDragOver"
              @dragleave.prevent="onDragLeave"
              @drop.prevent="onDrop"
              @click="() => fileInput.click()"
            >
              <input 
                type="file" 
                id="image" 
                ref="fileInput" 
                accept="image/png, image/jpeg, image/webp" 
                @change="handleFileChange" 
                class="file-input-hidden"
              />
              
              <div class="drop-zone-content">
                <div v-if="formModel.image" class="file-name-container">
                  <span class="file-name">✅ {{ formModel.image.name }}</span>
                  <button type="button" class="remove-image-btn" @click="removeImage" title="Remove image">✕</button>
                </div>
                <span v-else>
                  <template v-if="editingOutfitId">
                    <strong>Keep current image</strong> or choose a new file to replace it.<br>
                  </template>
                  <template v-else>
                    <strong>Choose a file</strong> or drag it here.<br>
                  </template>
                  <small>Also you can press PrintScreen, take a picture of the outfit in game, come here and just press Control+V (paste)</small>
                </span>
              </div>
            </div>
          </div>
          
          <!-- Alerts -->
          <div v-if="uploadError" class="alert error-alert">
            {{ uploadError }}
          </div>
          <div v-if="uploadSuccess" class="alert success-alert">
            {{ editingOutfitId ? 'Outfit updated successfully!' : 'Outfit uploaded successfully!' }}
          </div>

          <div class="form-actions">
            <button type="button" class="btn-cancel" @click="closeUploadModal" :disabled="isSubmitting">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="isSubmitting">
              <span v-if="isSubmitting">{{ editingOutfitId ? 'Saving...' : 'Uploading...' }}</span>
              <span v-else>{{ editingOutfitId ? 'Save Changes' : 'Submit Outfit' }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gallery-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
}

.gallery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
  flex-wrap: wrap;
  gap: var(--space-4);
}

.gallery-header h1 {
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

/* Filters */
.filters-container {
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-4);
}

.category-tabs {
  display: flex;
  background: var(--color-bg-secondary);
  padding: 4px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
}

.tab-btn {
  padding: 8px 24px;
  border-radius: var(--radius-full);
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-family: var(--font-heading);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn.active {
  background: var(--color-brand-primary);
  color: var(--color-text-inverse);
  box-shadow: var(--shadow-sm);
}

.tab-btn:hover:not(.active) {
  color: var(--color-text-primary);
}

/* Search & Filter Bar */
.search-filter-bar {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
  align-items: stretch;
}

.search-input-wrapper {
  flex: 1;
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

.uploader-filter-wrapper {
  flex-shrink: 0;
  min-width: 180px;
}

.uploader-select {
  width: 100%;
  height: 100%;
  padding: 10px 12px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: var(--font-size-base);
  cursor: pointer;
  transition: border-color 0.2s ease;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239ca3af' d='M3 4.5L6 7.5L9 4.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 32px;
}

.uploader-select:focus {
  outline: none;
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 3px rgba(163, 230, 53, 0.15);
}

/* Grid */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-6);
}

/* Empty State */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px dashed var(--color-border);
}

.no-results {
  text-align: center;
  color: var(--color-text-secondary);
}

.no-results .icon {
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
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--color-border);
}

.pagination-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-family: var(--font-body);
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
  box-shadow: 0 2px 8px rgba(163, 230, 53, 0.3);
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

/* Modal */
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

.modal-content {
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--color-border);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.modal-header h2 {
  font-family: var(--font-heading);
  margin: 0;
  color: var(--color-text-primary);
}

.btn-close {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.btn-close:hover {
  color: var(--color-text-primary);
}

.upload-form {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-row {
  display: flex;
  gap: var(--space-4);
}

.w-50 {
  flex: 1;
}

label {
  font-family: var(--font-heading);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

input, select, textarea {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  font-family: var(--font-body);
  transition: border-color 0.2s;
}

input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: var(--color-brand-primary);
}

.file-input-hidden {
  display: none;
}

.drop-zone {
  border: 2px dashed var(--color-border);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  padding: var(--space-6) var(--space-4);
  text-align: center;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.drop-zone:hover, .drop-zone.is-dragover {
  border-color: var(--color-brand-primary);
  background: rgba(163, 230, 53, 0.05);
}

.drop-zone-content {
  text-align: center;
  color: var(--color-text-secondary);
  pointer-events: none;
}

.file-name-container {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  pointer-events: auto;
}

.file-name {
  font-family: var(--font-data);
  color: var(--color-brand-primary);
  font-weight: 500;
  word-break: break-all;
}

.remove-image-btn {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.remove-image-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  transform: scale(1.1);
}

textarea {
  font-family: var(--font-data);
  resize: vertical;
}

.hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

/* Alerts */
.alert {
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.error-alert {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.success-alert {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-2);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

/* Buttons */
.btn-primary {
  background: var(--color-brand-primary);
  color: var(--color-text-inverse);
  border: none;
  padding: 10px 24px;
  border-radius: var(--radius-md);
  font-family: var(--font-heading);
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: background-color 0.2s, transform 0.1s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-brand-primary-hover);
  color: var(--color-bg-primary);
}

.btn-primary:active:not(:disabled) {
  transform: scale(0.98);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-cancel {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  padding: 10px 24px;
  border-radius: var(--radius-md);
  font-family: var(--font-heading);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

@media (max-width: 640px) {
  .search-filter-bar {
    flex-direction: column;
  }
  .uploader-filter-wrapper {
    min-width: unset;
  }
  .form-row {
    flex-direction: column;
    gap: var(--space-4);
  }
  .pagination-controls {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
