<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
import { useAuthStore } from '@/stores/auth'
import { useGuidesStore } from '@/stores/guides'
import { apiUrl } from '@/config/api'
import { CircleHelp } from 'lucide-vue-next'

const props = defineProps({
  visible: Boolean,
  editGuide: { type: Object, default: null }
})

const emit = defineEmits(['close', 'saved'])

const authStore = useAuthStore()
const guidesStore = useGuidesStore()

// Form state
const formModel = ref({
  title: '',
  guide_type: 'written',
  description: '',
  tags: '',
  author_name: '',
  content: '',
  youtube_url: ''
})

const thumbnailFile = ref(null)
const fileInput = ref(null)
const dragActive = ref(false)
const uploadError = ref('')
const uploadSuccess = ref(false)
const isSubmitting = ref(false)
const isUploadingImage = ref(false)
const showFormattingHelp = ref(false)

// Tag dropdown state
const showTagDropdown = ref(false)
const tagInput = ref('')

const isEditing = computed(() => !!props.editGuide)
const isVideo = computed(() => formModel.value.guide_type === 'video')

// Tag helpers
const selectedTags = computed(() => {
  if (!formModel.value.tags) return []
  return formModel.value.tags.split(',').map(t => t.trim()).filter(Boolean)
})

const availableTags = computed(() => {
  const search = tagInput.value.toLowerCase()
  return guidesStore.tags.filter(t =>
    !selectedTags.value.includes(t) &&
    t.toLowerCase().includes(search)
  )
})

function addTag(tag) {
  const current = selectedTags.value
  if (!current.includes(tag)) {
    current.push(tag)
    formModel.value.tags = current.join(',')
  }
  tagInput.value = ''
  showTagDropdown.value = false
}

function addCustomTag() {
  const tag = tagInput.value.trim()
  if (tag && !selectedTags.value.includes(tag)) {
    const current = selectedTags.value
    current.push(tag)
    formModel.value.tags = current.join(',')
  }
  tagInput.value = ''
  showTagDropdown.value = false
}

function removeTag(tag) {
  const current = selectedTags.value.filter(t => t !== tag)
  formModel.value.tags = current.join(',')
}

// ─── Image Upload Helper ─────────────────────────────────
async function uploadImageToServer(file: File): Promise<string | null> {
  const token = authStore.session?.access_token
  if (!token) {
    uploadError.value = 'You must be logged in to upload images.'
    return null
  }

  // Client-side guards
  if (!file.type.startsWith('image/')) {
    uploadError.value = 'Only image files can be inserted.'
    return null
  }
  if (file.size > 5 * 1024 * 1024) {
    uploadError.value = 'Image must be under 5 MB.'
    return null
  }

  isUploadingImage.value = true
  uploadError.value = ''

  try {
    const formData = new FormData()
    formData.append('image', file)

    const response = await fetch(apiUrl('/api/guides/images'), {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }))
      throw new Error(err.detail || 'Upload failed')
    }

    const data = await response.json()
    return data.url as string
  } catch (err: any) {
    uploadError.value = err.message || 'Failed to upload image.'
    return null
  } finally {
    isUploadingImage.value = false
  }
}

// ─── TipTap Editor ───────────────────────────────────────
const editor = useEditor({
  extensions: [
    StarterKit,
    Link.configure({ openOnClick: false }),
    Image.configure({ inline: true }),
  ],
  content: '',
  editorProps: {
    attributes: {
      class: 'tiptap-editor-content',
    },

    // Intercept pasted images from clipboard
    handlePaste(_view, event) {
      const items = event.clipboardData?.items
      if (!items) return false

      for (const item of items) {
        if (item.type.startsWith('image/')) {
          event.preventDefault()
          const file = item.getAsFile()
          if (file) {
            uploadImageToServer(file).then((url) => {
              if (url && editor.value) {
                editor.value.chain().focus().setImage({ src: url }).run()
              }
            })
          }
          return true
        }
      }
      return false
    },

    // Intercept dropped image files
    handleDrop(_view, event) {
      const files = event.dataTransfer?.files
      if (!files?.length) return false

      const file = files[0]
      if (file.type.startsWith('image/')) {
        event.preventDefault()
        uploadImageToServer(file).then((url) => {
          if (url && editor.value) {
            editor.value.chain().focus().setImage({ src: url }).run()
          }
        })
        return true
      }
      return false
    },
  },
})

// Populate form when editing
watch(() => props.visible, (val) => {
  if (val) {
    uploadError.value = ''
    uploadSuccess.value = false
    thumbnailFile.value = null

    if (props.editGuide) {
      formModel.value = {
        title: props.editGuide.title || '',
        guide_type: props.editGuide.guide_type || 'written',
        description: props.editGuide.description || '',
        tags: props.editGuide.tags || '',
        author_name: props.editGuide.author_name || '',
        content: props.editGuide.content || '',
        youtube_url: props.editGuide.youtube_url || ''
      }
      if (editor.value) {
        editor.value.commands.setContent(props.editGuide.content || '')
      }
    } else {
      formModel.value = {
        title: '',
        guide_type: 'written',
        description: '',
        tags: '',
        author_name: authStore.user?.user_metadata?.display_name || '',
        content: '',
        youtube_url: ''
      }
      if (editor.value) {
        editor.value.commands.setContent('')
      }
    }
  }
})

onMounted(() => {
  guidesStore.fetchTags()
})

// File handlers
function handleFileChange(e) {
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
    thumbnailFile.value = file
    uploadError.value = ''
    dragActive.value = false
  }
}

function removeThumbnail(e) {
  e.stopPropagation()
  thumbnailFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

// Editor toolbar actions
function setLink() {
  const url = window.prompt('Enter URL:')
  if (url && editor.value) {
    editor.value.chain().focus().setLink({ href: url }).run()
  }
}

function addImage() {
  const url = window.prompt('Enter image URL:')
  if (url && editor.value) {
    editor.value.chain().focus().setImage({ src: url }).run()
  }
}

// Submit
async function submitForm() {
  uploadError.value = ''
  uploadSuccess.value = false

  if (!formModel.value.title.trim()) {
    uploadError.value = 'Title is required.'
    return
  }

  if (isVideo.value && !formModel.value.youtube_url.trim()) {
    uploadError.value = 'YouTube URL is required for video guides.'
    return
  }

  isSubmitting.value = true

  try {
    // Sync editor content
    if (!isVideo.value && editor.value) {
      formModel.value.content = editor.value.getHTML()
    }

    const formData = new FormData()
    formData.append('title', formModel.value.title)
    formData.append('guide_type', formModel.value.guide_type)
    formData.append('description', formModel.value.description || '')
    formData.append('tags', formModel.value.tags || '')
    formData.append('author_name', formModel.value.author_name || authStore.user?.user_metadata?.display_name || 'Admin')
    formData.append('content', isVideo.value ? '' : (formModel.value.content || ''))
    formData.append('youtube_url', isVideo.value ? formModel.value.youtube_url : '')

    if (thumbnailFile.value) {
      formData.append('thumbnail', thumbnailFile.value)
    }

    const token = authStore.session?.access_token

    if (isEditing.value) {
      await guidesStore.updateGuide(props.editGuide.id, formData, token)
    } else {
      await guidesStore.createGuide(formData, token)
    }

    uploadSuccess.value = true
    setTimeout(() => {
      emit('saved')
      emit('close')
    }, 1200)
  } catch (err) {
    uploadError.value = err.message || 'Failed to save guide.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>{{ isEditing ? 'Edit Guide' : 'Add New Guide' }}</h2>
        <button class="btn-close" @click="emit('close')">✕</button>
      </div>

      <form @submit.prevent="submitForm" class="guide-form">
        <!-- Guide Type Selector -->
        <div class="form-group">
          <label>Guide Type</label>
          <div class="type-selector">
            <button
              type="button"
              class="type-btn"
              :class="{ active: formModel.guide_type === 'written' }"
              @click="formModel.guide_type = 'written'"
            >
              📖 Written Article
            </button>
            <button
              type="button"
              class="type-btn"
              :class="{ active: formModel.guide_type === 'video' }"
              @click="formModel.guide_type = 'video'"
            >
              📹 Video Guide
            </button>
          </div>
        </div>

        <!-- Title -->
        <div class="form-group">
          <label for="guide-title">Title</label>
          <input
            id="guide-title"
            v-model="formModel.title"
            required
            placeholder="e.g. How to Set Up Your First Online Match"
          />
        </div>

        <!-- Description -->
        <div class="form-group">
          <label for="guide-desc">Short Description</label>
          <input
            id="guide-desc"
            v-model="formModel.description"
            placeholder="Brief summary shown on the card"
          />
        </div>

        <!-- Author Name -->
        <div class="form-group">
          <label for="guide-author">Author Name</label>
          <input id="guide-author" v-model="formModel.author_name" placeholder="Your name" />
        </div>

        <!-- Tags (Dropdown) -->
        <div class="form-group tag-group">
          <label>Tags</label>
          <div class="selected-tags" v-if="selectedTags.length">
            <span v-for="tag in selectedTags" :key="tag" class="tag-chip">
              {{ tag }}
              <button type="button" class="remove-tag" @click="removeTag(tag)">×</button>
            </span>
          </div>
          <div class="tag-dropdown-wrapper">
            <input
              v-model="tagInput"
              class="tag-input"
              placeholder="Search or add a tag..."
              @focus="showTagDropdown = true"
              @keydown.enter.prevent="addCustomTag"
            />
            <div v-if="showTagDropdown" class="tag-dropdown" @mousedown.prevent>
              <button
                v-for="tag in availableTags"
                :key="tag"
                type="button"
                class="tag-option"
                @click="addTag(tag)"
              >
                {{ tag }}
              </button>
              <button
                v-if="tagInput.trim() && !guidesStore.tags.includes(tagInput.trim())"
                type="button"
                class="tag-option new-tag"
                @click="addCustomTag"
              >
                + Add "{{ tagInput.trim() }}"
              </button>
              <div v-if="!availableTags.length && !tagInput.trim()" class="tag-empty">
                No tags available. Type to create one.
              </div>
            </div>
          </div>
          <div class="click-away" v-if="showTagDropdown" @click="showTagDropdown = false" />
        </div>

        <!-- YouTube URL (Video only) -->
        <div v-if="isVideo" class="form-group">
          <label for="guide-yt">YouTube URL</label>
          <input
            id="guide-yt"
            v-model="formModel.youtube_url"
            required
            placeholder="https://www.youtube.com/watch?v=..."
          />
        </div>

        <!-- TipTap Editor (Written only) -->
        <div v-if="!isVideo" class="form-group">
          <div class="content-label-row">
            <label>Content</label>
            <button type="button" class="help-toggle" @click="showFormattingHelp = !showFormattingHelp" title="Formatting guide">
              <CircleHelp :size="16" /> Formatting Guide
            </button>
          </div>

          <!-- Formatting Help Tooltip -->
          <Transition name="help-fade">
            <div v-if="showFormattingHelp" class="formatting-help">
              <div class="help-header">
                <strong>✨ Formatting Guide</strong>
                <button type="button" class="help-close" @click="showFormattingHelp = false">✕</button>
              </div>
              <div class="help-grid">
                <div class="help-section">
                  <h4>📝 Text</h4>
                  <ul>
                    <li><strong>B</strong> — Bold</li>
                    <li><em>I</em> — Italic</li>
                    <li><strong>H2 / H3</strong> — Headings</li>
                    <li><strong>•</strong> / <strong>1.</strong> — Lists</li>
                    <li><strong>❝</strong> — Blockquote</li>
                    <li><strong>&lt;/&gt;</strong> — Code block</li>
                  </ul>
                </div>
                <div class="help-section">
                  <h4>🖼️ Images</h4>
                  <ul>
                    <li><strong>Paste</strong> — Ctrl+V / Cmd+V a copied image</li>
                    <li><strong>Drag & Drop</strong> — Drop an image file into the editor</li>
                    <li><strong>🖼️ button</strong> — Insert by URL</li>
                  </ul>
                </div>
                <div class="help-section">
                  <h4>🔗 Links</h4>
                  <ul>
                    <li>Select text → click <strong>🔗</strong> → enter URL</li>
                  </ul>
                </div>
              </div>
            </div>
          </Transition>

          <div class="editor-toolbar">
            <button type="button" @click="editor?.chain().focus().toggleBold().run()" :class="{ 'is-active': editor?.isActive('bold') }" title="Bold">
              <strong>B</strong>
            </button>
            <button type="button" @click="editor?.chain().focus().toggleItalic().run()" :class="{ 'is-active': editor?.isActive('italic') }" title="Italic">
              <em>I</em>
            </button>
            <button type="button" @click="editor?.chain().focus().toggleHeading({ level: 2 }).run()" :class="{ 'is-active': editor?.isActive('heading', { level: 2 }) }" title="Heading">
              H2
            </button>
            <button type="button" @click="editor?.chain().focus().toggleHeading({ level: 3 }).run()" :class="{ 'is-active': editor?.isActive('heading', { level: 3 }) }" title="Heading 3">
              H3
            </button>
            <button type="button" @click="editor?.chain().focus().toggleBulletList().run()" :class="{ 'is-active': editor?.isActive('bulletList') }" title="Bullet List">
              •
            </button>
            <button type="button" @click="editor?.chain().focus().toggleOrderedList().run()" :class="{ 'is-active': editor?.isActive('orderedList') }" title="Ordered List">
              1.
            </button>
            <button type="button" @click="setLink" :class="{ 'is-active': editor?.isActive('link') }" title="Link">
              🔗
            </button>
            <button type="button" @click="addImage" title="Insert image by URL">
              🖼️
            </button>
            <button type="button" @click="editor?.chain().focus().toggleBlockquote().run()" :class="{ 'is-active': editor?.isActive('blockquote') }" title="Quote">
              ❝
            </button>
            <button type="button" @click="editor?.chain().focus().toggleCodeBlock().run()" :class="{ 'is-active': editor?.isActive('codeBlock') }" title="Code Block">
              &lt;/&gt;
            </button>
          </div>

          <!-- Upload indicator -->
          <div v-if="isUploadingImage" class="upload-indicator">
            <div class="upload-spinner"></div>
            <span>Uploading image…</span>
          </div>

          <div class="editor-container">
            <EditorContent :editor="editor" />
          </div>
        </div>

        <!-- Thumbnail Upload -->
        <div class="form-group">
          <label>Thumbnail Image {{ isVideo ? '(Optional — auto-generated from YouTube)' : '' }}</label>
          <div
            class="drop-zone"
            :class="{ 'is-dragover': dragActive }"
            @dragover.prevent="dragActive = true"
            @dragleave.prevent="dragActive = false"
            @drop.prevent="(e) => handleFileChange(e)"
            @click="() => fileInput.click()"
          >
            <input
              type="file"
              ref="fileInput"
              accept="image/png, image/jpeg, image/webp"
              @change="handleFileChange"
              class="file-input-hidden"
            />
            <div class="drop-zone-content">
              <div v-if="thumbnailFile" class="file-name-container">
                <span class="file-name">✅ {{ thumbnailFile.name }}</span>
                <button type="button" class="remove-image-btn" @click="removeThumbnail" title="Remove image">✕</button>
              </div>
              <span v-else>
                <template v-if="isEditing && !thumbnailFile">
                  <strong>Keep current thumbnail</strong> or choose a new file to replace it.<br>
                </template>
                <template v-else>
                  <strong>Choose a file</strong> or drag it here.<br>
                </template>
                <small>PNG, JPEG, or WebP — max 5MB</small>
              </span>
            </div>
          </div>
        </div>

        <!-- Alerts -->
        <div v-if="uploadError" class="alert error-alert">{{ uploadError }}</div>
        <div v-if="uploadSuccess" class="alert success-alert">
          {{ isEditing ? 'Guide updated successfully!' : 'Guide created successfully!' }}
        </div>

        <div class="form-actions">
          <button type="button" class="btn-cancel" @click="emit('close')" :disabled="isSubmitting">Cancel</button>
          <button type="submit" class="btn-primary" :disabled="isSubmitting">
            <span v-if="isSubmitting">{{ isEditing ? 'Saving...' : 'Creating...' }}</span>
            <span v-else>{{ isEditing ? 'Save Changes' : 'Create Guide' }}</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
/* Modal overlay */
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
  max-width: 720px;
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
  position: sticky;
  top: 0;
  background: var(--color-bg-primary);
  z-index: 1;
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

/* Form */
.guide-form {
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

label {
  font-family: var(--font-heading);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

input, textarea, select {
  padding: 10px 14px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-family: var(--font-body);
  font-size: var(--font-size-base);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

input:focus, textarea:focus, select:focus {
  outline: none;
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 3px rgba(163, 230, 53, 0.15);
}

/* Type Selector */
.type-selector {
  display: flex;
  gap: var(--space-2);
}

.type-btn {
  flex: 1;
  padding: 10px 16px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  font-family: var(--font-heading);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.type-btn.active {
  border-color: var(--color-brand-primary);
  background: rgba(163, 230, 53, 0.1);
  color: var(--color-brand-primary);
}

.type-btn:hover:not(.active) {
  border-color: var(--color-text-muted);
  color: var(--color-text-primary);
}

/* Tag dropdown */
.tag-group {
  position: relative;
}

.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 4px;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(163, 230, 53, 0.15);
  color: var(--color-brand-primary);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.remove-tag {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 14px;
  padding: 0 2px;
  opacity: 0.7;
}

.remove-tag:hover {
  opacity: 1;
}

.tag-dropdown-wrapper {
  position: relative;
}

.tag-input {
  width: 100%;
}

.tag-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  max-height: 200px;
  overflow-y: auto;
  z-index: 20;
  box-shadow: var(--shadow-lg);
  margin-top: 4px;
}

.tag-option {
  display: block;
  width: 100%;
  text-align: left;
  padding: 8px 14px;
  background: transparent;
  border: none;
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: var(--font-size-sm);
  transition: background 0.1s ease;
}

.tag-option:hover {
  background: var(--color-bg-hover);
}

.tag-option.new-tag {
  color: var(--color-brand-primary);
  font-weight: 600;
  border-top: 1px solid var(--color-border);
}

.tag-empty {
  padding: 12px 14px;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  text-align: center;
}

.click-away {
  position: fixed;
  inset: 0;
  z-index: 10;
}

/* Content label row */
.content-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.help-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.help-toggle:hover {
  color: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
  background: rgba(163, 230, 53, 0.06);
}

/* Formatting Help Popup */
.formatting-help {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-2);
}

.help-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.help-close {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 1rem;
  padding: 2px 4px;
}

.help-close:hover {
  color: var(--color-text-primary);
}

.help-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--space-4);
}

.help-section h4 {
  font-size: var(--font-size-xs);
  font-weight: 700;
  margin: 0 0 var(--space-2) 0;
  color: var(--color-text-primary);
}

.help-section ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.help-section li {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  padding: 2px 0;
  line-height: 1.5;
}

/* Help fade transition */
.help-fade-enter-active,
.help-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.help-fade-enter-from,
.help-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* Upload indicator */
.upload-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 8px 14px;
  background: rgba(163, 230, 53, 0.08);
  border: 1px solid rgba(163, 230, 53, 0.2);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-brand-primary);
  animation: pulse-bg 1.5s ease-in-out infinite;
}

.upload-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(163, 230, 53, 0.3);
  border-top-color: var(--color-brand-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes pulse-bg {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* Editor */
.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-bottom: none;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.editor-toolbar button {
  padding: 6px 10px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-family: var(--font-heading);
  transition: all 0.15s ease;
  min-width: 32px;
}

.editor-toolbar button:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.editor-toolbar button.is-active {
  background: rgba(163, 230, 53, 0.15);
  color: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
}

.editor-container {
  border: 1px solid var(--color-border);
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  min-height: 250px;
  background: var(--color-bg-secondary);
}

/* TipTap content styling */
.editor-container :deep(.tiptap-editor-content) {
  padding: 14px;
  min-height: 250px;
  color: var(--color-text-primary);
  font-family: var(--font-body);
  font-size: var(--font-size-base);
  line-height: 1.7;
  outline: none;
}

.editor-container :deep(.tiptap-editor-content h2) {
  font-size: var(--font-size-xl);
  font-weight: 700;
  margin: 1em 0 0.5em;
  color: var(--color-text-primary);
}

.editor-container :deep(.tiptap-editor-content h3) {
  font-size: var(--font-size-lg);
  font-weight: 600;
  margin: 0.8em 0 0.4em;
  color: var(--color-text-primary);
}

.editor-container :deep(.tiptap-editor-content p) {
  margin: 0.5em 0;
}

.editor-container :deep(.tiptap-editor-content a) {
  color: var(--color-brand-primary);
  text-decoration: underline;
}

.editor-container :deep(.tiptap-editor-content img) {
  max-width: 100%;
  border-radius: var(--radius-md);
  margin: 0.5em 0;
}

.editor-container :deep(.tiptap-editor-content ul),
.editor-container :deep(.tiptap-editor-content ol) {
  padding-left: 1.5em;
  margin: 0.5em 0;
}

.editor-container :deep(.tiptap-editor-content blockquote) {
  border-left: 3px solid var(--color-brand-primary);
  padding-left: 1em;
  margin: 0.5em 0;
  color: var(--color-text-secondary);
}

.editor-container :deep(.tiptap-editor-content pre) {
  background: var(--color-bg-primary);
  border-radius: var(--radius-md);
  padding: 1em;
  overflow-x: auto;
  font-family: 'Fira Code', monospace;
  font-size: var(--font-size-sm);
}

/* Drop zone */
.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.drop-zone:hover,
.drop-zone.is-dragover {
  border-color: var(--color-brand-primary);
  background: rgba(163, 230, 53, 0.05);
}

.file-input-hidden {
  display: none;
}

.drop-zone-content {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.file-name-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.file-name {
  color: var(--color-brand-primary);
  font-weight: 600;
}

.remove-image-btn {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: var(--color-error);
  border-radius: var(--radius-sm);
  cursor: pointer;
  padding: 2px 6px;
  font-size: var(--font-size-xs);
}

/* Alerts */
.alert {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
}

.error-alert {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: var(--color-error);
}

.success-alert {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  color: var(--color-success);
}

/* Actions */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding-top: var(--space-2);
}

.btn-cancel {
  padding: 10px 20px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-cancel:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

.btn-primary {
  padding: 10px 24px;
  background: var(--color-brand-primary);
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-inverse);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  filter: brightness(1.1);
  box-shadow: 0 2px 8px rgba(163, 230, 53, 0.3);
}

.btn-primary:disabled,
.btn-cancel:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
