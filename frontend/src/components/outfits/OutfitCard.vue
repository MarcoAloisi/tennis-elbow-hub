<script setup>
import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useOutfitsStore } from '@/stores/outfits'

const props = defineProps({
  outfit: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['edit'])

const authStore = useAuthStore()
const outfitsStore = useOutfitsStore()
const copied = ref(false)
const isDeleting = ref(false)

const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(props.outfit.outfit_code)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy text: ', err)
  }
}

const deleteOutfit = async () => {
  if (confirm('Are you sure you want to delete this outfit? This action cannot be undone.')) {
    isDeleting.value = true
    try {
      await outfitsStore.deleteOutfit(props.outfit.id, authStore.session?.access_token)
    } catch (err) {
      console.error('Failed to delete outfit:', err)
      alert('Failed to delete outfit. Please try again.')
      isDeleting.value = false
    }
  }
}

// Format the date (e.g., "Feb 20, 2026")
const formattedDate = computed(() => {
  if (!props.outfit.created_at) return ''
  const date = new Date(props.outfit.created_at)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  }).format(date)
})

</script>

<template>
  <div class="outfit-card">
    <div class="image-container">
      <img :src="outfit.image_url" :alt="outfit.title" class="outfit-image" loading="lazy" />
      <div class="category-badge">
        {{ outfit.category }}
      </div>
    </div>
    
    <div class="card-content">
      <h3 class="outfit-title">{{ outfit.title }}</h3>
      
      <div class="meta-info">
        <span class="uploader">
          <span class="icon">👤</span> {{ outfit.uploader_name }}
        </span>
        <span class="date">{{ formattedDate }}</span>
      </div>
      
      <div v-if="authStore.user" class="admin-actions">
        <button class="btn-edit" @click="emit('edit', outfit)" title="Edit Outfit">
          ✏️ Edit
        </button>
        <button class="btn-delete" @click="deleteOutfit" :disabled="isDeleting" title="Delete Outfit">
          <span v-if="isDeleting">🗑️...</span>
          <span v-else>🗑️ Delete</span>
        </button>
      </div>
      
      <div class="code-section">
        <div class="code-preview" :title="outfit.outfit_code">
          {{ outfit.outfit_code }}
        </div>
        <button 
          class="btn-copy" 
          :class="{ 'copied': copied }"
          @click="copyCode"
          :title="copied ? 'Copied!' : 'Copy to clipboard'"
        >
          <span v-if="copied">✓ Copied</span>
          <span v-else>📋 Copy Code</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.outfit-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all var(--transition-base);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.outfit-card:hover {
  border-color: var(--color-brand-primary);
  box-shadow: var(--shadow-md);
  transform: translateY(-4px);
}

.image-container {
  position: relative;
  width: 100%;
  padding-top: 100%; /* 1:1 Aspect Ratio (Square) by default */
  background-color: var(--color-bg-tertiary);
  overflow: hidden;
}

.outfit-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain; /* Often better for outfits to avoid cropping */
  transition: transform 0.5s ease;
}

.outfit-card:hover .outfit-image {
  transform: scale(1.05);
}

.category-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background-color: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(4px);
  color: #ffffff;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: var(--font-size-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 2px 4px rgba(0,0,0,0.3);
}

.card-content {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  flex-grow: 1;
}

.outfit-title {
  font-family: var(--font-heading);
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2) 0;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.meta-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.uploader {
  display: flex;
  align-items: center;
  gap: 4px;
}

.code-section {
  margin-top: auto; /* Push to bottom */
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.code-preview {
  font-family: var(--font-data);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  background: var(--color-bg-tertiary);
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-copy {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 8px 16px;
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: var(--font-heading);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-copy:hover {
  background-color: var(--color-bg-hover);
  border-color: var(--color-brand-primary);
  color: var(--color-brand-primary);
}

.btn-copy.copied {
  background-color: rgba(34, 197, 94, 0.1);
  border-color: var(--color-brand-live);
  color: var(--color-brand-live);
}

.admin-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.btn-edit {
  background: transparent;
  color: var(--color-brand-primary);
  border: 1px solid rgba(163, 230, 53, 0.3);
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-family: var(--font-heading);
  font-size: var(--font-size-xs);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-edit:hover {
  background: rgba(163, 230, 53, 0.1);
  border-color: var(--color-brand-primary);
}

.btn-delete {
  background: transparent;
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-family: var(--font-heading);
  font-size: var(--font-size-xs);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-delete:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.1);
  border-color: #ef4444;
}

.btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
