<script setup>
import { computed, onMounted, ref } from 'vue'
import { useOutfitsStore } from '@/stores/outfits'
import { useAuthStore } from '@/stores/auth'
import OutfitCard from '@/components/outfits/OutfitCard.vue'

const outfitsStore = useOutfitsStore()
const authStore = useAuthStore()

// State
const isUploadModalOpen = ref(false)
const selectedCategory = ref('All')
const categories = ['All', 'Male', 'Female']

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

onMounted(() => {
  outfitsStore.fetchOutfits()
})

const filteredOutfits = computed(() => {
  if (selectedCategory.value === 'All') return outfitsStore.outfits
  return outfitsStore.outfits.filter(o => o.category === selectedCategory.value)
})

const setCategory = (cat) => {
  selectedCategory.value = cat
  outfitsStore.fetchOutfits(cat)
}

const handleFileChange = (e) => {
  const file = e.dataTransfer ? e.dataTransfer.files[0] : e.target.files[0]
  if (file) {
    // Validate it's an image
    if (!file.type.startsWith('image/')) {
      uploadError.value = 'Please upload a valid image file.'
      if (fileInput.value) fileInput.value.value = ''
      dragActive.value = false
      return
    }
    // Limit size to 5MB
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

const dragActive = ref(false)

const onDragOver = (e) => {
  dragActive.value = true
}

const onDragLeave = (e) => {
  dragActive.value = false
}

const onDrop = (e) => {
  handleFileChange(e)
}

const handlePaste = (e) => {
  // Ignore paste if they are typing in an input text/textarea
  if (e.target.tagName === 'INPUT' && e.target.type !== 'file') return
  if (e.target.tagName === 'TEXTAREA') return

  if (e.clipboardData && e.clipboardData.files && e.clipboardData.files.length > 0) {
    e.preventDefault()
    handleFileChange({ target: { files: e.clipboardData.files } })
  }
}

onMounted(() => {
  outfitsStore.fetchOutfits()
  window.addEventListener('paste', handlePaste)
})

import { onUnmounted } from 'vue'

onUnmounted(() => {
  window.removeEventListener('paste', handlePaste)
})

const submitForm = async () => {
  uploadError.value = ''
  uploadSuccess.value = false
  
  if (!formModel.value.image) {
    uploadError.value = 'Please select an image to upload.'
    return
  }
  
  isSubmitting.value = true
  
  try {
    const formData = new FormData()
    formData.append('title', formModel.value.title)
    formData.append('outfit_code', formModel.value.outfit_code)
    formData.append('category', formModel.value.category)
    // If the user didn't provide a name, fallback to their account display name
    formData.append('uploader_name', formModel.value.uploader_name || authStore.user?.user_metadata?.display_name || 'Anonymous')
    formData.append('image', formModel.value.image)
    
    // Pass the JWT session token instead of the manual secret
    const token = authStore.session?.access_token
    await outfitsStore.createOutfit(formData, token)
    
    uploadSuccess.value = true
    setTimeout(() => {
      closeUploadModal()
    }, 1500)
    
  } catch (err) {
    uploadError.value = err.message || 'Failed to upload outfit.'
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
  // Reset form
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
      <button v-if="authStore.user" class="btn-primary" @click="openUploadModal">
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

    <!-- Gallery Grid -->
    <div class="gallery-grid" v-if="filteredOutfits.length > 0">
      <div v-for="outfit in filteredOutfits" :key="outfit.id" class="grid-item">
        <OutfitCard :outfit="outfit" />
      </div>
    </div>
    
    <!-- Empty State / Loading -->
    <div v-else class="empty-state">
      <div v-if="outfitsStore.loading" class="loading-spinner"></div>
      <div v-else class="no-results">
        <div class="icon">👕</div>
        <h3>No outfits found</h3>
        <p>There are currently no outfits uploaded for this category.</p>
      </div>
    </div>

    <!-- Upload Modal -->
    <div v-if="isUploadModalOpen" class="modal-overlay" @click.self="closeUploadModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Upload New Outfit</h2>
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
                required
                class="file-input-hidden"
              />
              
              <div class="drop-zone-content">
                <span v-if="formModel.image" class="file-name">✅ {{ formModel.image.name }}</span>
                <span v-else>
                  <strong>Choose a file</strong> or drag it here.<br>
                  <small>You can also paste (Ctrl+V) an image directly!</small>
                </span>
              </div>
            </div>
          </div>
          
          <!-- Alerts -->
          <div v-if="uploadError" class="alert error-alert">
            {{ uploadError }}
          </div>
          <div v-if="uploadSuccess" class="alert success-alert">
            Outfit uploaded successfully!
          </div>

          <div class="form-actions">
            <button type="button" class="btn-cancel" @click="closeUploadModal" :disabled="isSubmitting">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="isSubmitting">
              <span v-if="isSubmitting">Uploading...</span>
              <span v-else>Submit Outfit</span>
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
  margin-bottom: var(--space-8);
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
  background: rgba(163, 230, 53, 0.05); /* very light neon tint */
}

.drop-zone-content strong {
  color: var(--color-text-primary);
}

.file-name {
  color: var(--color-brand-primary);
  font-weight: 600;
  word-break: break-all;
}

textarea {
  font-family: var(--font-data);
  resize: vertical;
}

.hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.highlight-box {
  background: rgba(239, 68, 68, 0.05); /* subtle red tint */
  border: 1px dashed rgba(239, 68, 68, 0.3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
}

.highlight-box label {
  color: #ef4444; /* red-500 */
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
  .form-row {
    flex-direction: column;
    gap: var(--space-4);
  }
}
</style>
