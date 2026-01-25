<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  isLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['upload'])

const isDragging = ref(false)
const fileInput = ref(null)
const selectedFile = ref(null)
const errorMessage = ref('')

const allowedTypes = ['text/html', 'text/htm', 'application/xhtml+xml']
const maxSizeMB = 10

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
  
  const files = e.dataTransfer?.files
  if (files?.length) {
    validateAndSelect(files[0])
  }
}

function handleFileSelect(e) {
  const files = e.target?.files
  if (files?.length) {
    validateAndSelect(files[0])
  }
}

function validateAndSelect(file) {
  errorMessage.value = ''
  
  // Check file type
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['html', 'htm'].includes(ext)) {
    errorMessage.value = 'Please upload an HTML file (.html or .htm)'
    return
  }
  
  // Check file size
  if (file.size > maxSizeMB * 1024 * 1024) {
    errorMessage.value = `File too large. Maximum size is ${maxSizeMB}MB`
    return
  }
  
  selectedFile.value = file
}

function triggerFileSelect() {
  fileInput.value?.click()
}

function uploadFile() {
  if (selectedFile.value) {
    emit('upload', selectedFile.value)
  }
}

function clearSelection() {
  selectedFile.value = null
  errorMessage.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// Format file size
function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<template>
  <div class="file-uploader">
    <!-- Drop Zone -->
    <div 
      class="drop-zone"
      :class="{ 'is-dragging': isDragging, 'has-file': selectedFile }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
      @click="triggerFileSelect"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".html,.htm"
        @change="handleFileSelect"
        hidden
      />
      
      <template v-if="!selectedFile">
        <div class="drop-icon">📄</div>
        <h4 class="drop-title">Drop your match log here</h4>
        <p class="drop-subtitle">or click to browse</p>
        <p class="drop-hint">Supports HTML files from Tennis Elbow 4</p>
      </template>
      
      <template v-else>
        <div class="file-preview">
          <div class="file-icon">📋</div>
          <div class="file-info">
            <span class="file-name">{{ selectedFile.name }}</span>
            <span class="file-size">{{ formatSize(selectedFile.size) }}</span>
          </div>
          <button 
            class="file-remove" 
            @click.stop="clearSelection"
            title="Remove file"
          >
            ✕
          </button>
        </div>
      </template>
    </div>

    <!-- Error Message -->
    <p v-if="errorMessage" class="upload-error">
      {{ errorMessage }}
    </p>

    <!-- Upload Button -->
    <button 
      v-if="selectedFile"
      class="btn btn-primary btn-lg upload-btn"
      :disabled="isLoading"
      @click="uploadFile"
    >
      <span v-if="isLoading" class="spinner"></span>
      <span v-else>📊</span>
      {{ isLoading ? 'Analyzing...' : 'Analyze Match' }}
    </button>
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

.file-preview {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-bg-primary);
  border-radius: var(--radius-md);
}

.file-icon {
  font-size: 2rem;
}

.file-info {
  flex: 1;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.file-name {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  word-break: break-all;
}

.file-size {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.file-remove {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.file-remove:hover {
  background: var(--color-error-light);
  color: var(--color-error);
}

.upload-error {
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

.upload-btn {
  min-width: 200px;
}

.upload-btn .spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
