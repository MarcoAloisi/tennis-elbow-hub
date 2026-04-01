<script setup lang="ts">
import { ref } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  isLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['upload'])

const isDragging = ref(false)
const fileInput = ref(null)
const selectedFiles = ref<File[]>([])
const errorMessage = ref('')

const maxSizeMB = 10
const maxFiles = 20

function handleDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

function handleDrop(e) {
  e.preventDefault()
  isDragging.value = false
  
  const files = Array.from(e.dataTransfer?.files || []) as File[]
  if (files.length) {
    validateAndAddFiles(files)
  }
}

function handleFileSelect(e) {
  const files = Array.from(e.target?.files || []) as File[]
  if (files.length) {
    validateAndAddFiles(files)
  }
  // Reset the input so the same files can be selected again
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function validateAndAddFiles(files: File[]) {
  errorMessage.value = ''
  
  // Check max files limit
  if (selectedFiles.value.length + files.length > maxFiles) {
    errorMessage.value = `You can upload up to ${maxFiles} files at once. Currently selected: ${selectedFiles.value.length}`
    return
  }
  
  const validFiles: File[] = []
  
  for (const file of files) {
    // Check file type
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!['html', 'htm'].includes(ext || '')) {
      errorMessage.value = `"${file.name}" is not an HTML file. Only .html and .htm files are supported.`
      continue
    }
    
    // Check file size
    if (file.size > maxSizeMB * 1024 * 1024) {
      errorMessage.value = `"${file.name}" is too large. Maximum size is ${maxSizeMB}MB per file.`
      continue
    }
    
    // Avoid duplicates by name
    if (selectedFiles.value.some(f => f.name === file.name && f.size === file.size)) {
      continue
    }
    
    validFiles.push(file)
  }
  
  selectedFiles.value = [...selectedFiles.value, ...validFiles]
}

function triggerFileSelect() {
  fileInput.value?.click()
}

function uploadFiles() {
  if (selectedFiles.value.length > 0) {
    emit('upload', selectedFiles.value)
  }
}

function removeFile(index: number) {
  selectedFiles.value = selectedFiles.value.filter((_, i) => i !== index)
  errorMessage.value = ''
}

function clearSelection() {
  selectedFiles.value = []
  errorMessage.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// Format file size
function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const totalSize = () => {
  return selectedFiles.value.reduce((sum, f) => sum + f.size, 0)
}
</script>

<template>
  <div class="file-uploader">
    <!-- Drop Zone -->
    <div 
      class="drop-zone"
      :class="{ 'is-dragging': isDragging, 'has-file': selectedFiles.length > 0 }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
      @click="triggerFileSelect"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".html,.htm"
        multiple
        @change="handleFileSelect"
        hidden
      />
      
      <template v-if="selectedFiles.length === 0">
        <div class="drop-icon">📄</div>
        <h4 class="drop-title">Drop your match logs here</h4>
        <p class="drop-subtitle">or click to browse</p>
        <p class="drop-hint">Supports multiple HTML files from Tennis Elbow 4</p>
      </template>
      
      <template v-else>
        <div class="files-preview" @click.stop>
          <div class="files-header">
            <span class="files-count">{{ selectedFiles.length }} file{{ selectedFiles.length > 1 ? 's' : '' }} selected</span>
            <span class="files-total-size">{{ formatSize(totalSize()) }}</span>
          </div>
          <div class="files-list">
            <div v-for="(file, index) in selectedFiles" :key="file.name + file.size" class="file-item">
              <div class="file-icon">📋</div>
              <div class="file-info">
                <span class="file-name">{{ file.name }}</span>
                <span class="file-size">{{ formatSize(file.size) }}</span>
              </div>
              <button 
                class="file-remove" 
                @click.stop="removeFile(index)"
                title="Remove file"
              >
                <X :size="14" />
              </button>
            </div>
          </div>
          <button class="add-more-btn" @click.stop="triggerFileSelect">
            + Add more files
          </button>
        </div>
      </template>
    </div>

    <!-- Error Message -->
    <p v-if="errorMessage" class="upload-error">
      {{ errorMessage }}
    </p>

    <!-- Upload Button -->
    <div v-if="selectedFiles.length > 0" class="upload-actions">
      <button 
        class="btn btn-ghost btn-md clear-btn"
        @click="clearSelection"
        :disabled="isLoading"
      >
        Clear All
      </button>
      <button 
        class="btn btn-primary btn-lg upload-btn"
        :disabled="isLoading"
        @click="uploadFiles"
      >
        <span v-if="isLoading" class="spinner"></span>
        <span v-else>📊</span>
        {{ isLoading ? 'Analyzing...' : `Analyze ${selectedFiles.length} File${selectedFiles.length > 1 ? 's' : ''}` }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.file-uploader {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}

.drop-zone {
  width: 100%;
  max-width: 500px;
  padding: var(--space-10);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-bg-secondary);
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-base);
}

.drop-zone:hover,
.drop-zone.is-dragging {
  border-color: var(--color-accent);
  background: var(--color-accent-light);
}

.drop-zone.has-file {
  border-style: solid;
  border-color: var(--color-success);
  background: var(--color-success-light);
  padding: var(--space-5);
  cursor: default;
}

.drop-icon {
  font-size: 3rem;
  margin-bottom: var(--space-4);
  opacity: 0.7;
}

.drop-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.drop-subtitle {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}

.drop-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

/* Multi-file preview */
.files-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: 100%;
}

.files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.files-count {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.files-total-size {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-height: 240px;
  overflow-y: auto;
  padding-right: var(--space-1);
}

.files-list::-webkit-scrollbar {
  width: 4px;
}

.files-list::-webkit-scrollbar-track {
  background: transparent;
}

.files-list::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: var(--radius-full);
}

.file-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-primary);
  border-radius: var(--radius-md);
  transition: background-color var(--transition-fast);
}

.file-item:hover {
  background: var(--color-bg-secondary);
}

.file-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.file-name {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.file-remove {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-text-muted);
  transition: all var(--transition-fast);
  flex-shrink: 0;
  cursor: pointer;
}

.file-remove:hover {
  background: var(--color-error-light);
  color: var(--color-error);
}

.add-more-btn {
  padding: var(--space-2);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.add-more-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-light);
}

.upload-error {
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

.upload-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.clear-btn {
  color: var(--color-text-muted);
}

.upload-btn {
  min-width: 200px;
}

.upload-btn .spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: var(--color-text-inverse);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
