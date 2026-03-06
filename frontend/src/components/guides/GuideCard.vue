<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Video, BookOpen, Pencil, Trash2 } from 'lucide-vue-next'

const props = defineProps({
  guide: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['edit', 'delete'])

const router = useRouter()
const authStore = useAuthStore()

const isVideo = computed(() => props.guide.guide_type === 'video')

const thumbnailUrl = computed(() => {
  if (props.guide.thumbnail_url) return props.guide.thumbnail_url
  // Auto-generate YouTube thumbnail for video guides
  if (isVideo.value && props.guide.youtube_url) {
    const id = extractYoutubeId(props.guide.youtube_url)
    if (id) return `https://img.youtube.com/vi/${id}/maxresdefault.jpg`
  }
  return null
})

const tagList = computed(() => {
  if (!props.guide.tags) return []
  return props.guide.tags.split(',').map(t => t.trim()).filter(Boolean)
})

function extractYoutubeId(url) {
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/)
  return match ? match[1] : null
}

function openGuide() {
  router.push({ name: 'GuideDetail', params: { slug: props.guide.slug } })
}
</script>

<template>
  <div class="guide-card" @click="openGuide">
    <!-- Thumbnail -->
    <div class="guide-thumbnail">
      <img v-if="thumbnailUrl" :src="thumbnailUrl" :alt="guide.title" class="thumbnail-img" />
      <div v-else class="thumbnail-placeholder">
        <Video v-if="isVideo" :size="48" class="placeholder-icon" />
        <BookOpen v-else :size="48" class="placeholder-icon" />
      </div>

      <!-- Type Badge -->
      <span class="type-badge" :class="guide.guide_type">
        <Video v-if="isVideo" :size="14" class="inline-icon" />
        <BookOpen v-else :size="14" class="inline-icon" />
        {{ isVideo ? 'Video' : 'Article' }}
      </span>

      <!-- Play icon overlay for video guides -->
      <div v-if="isVideo" class="play-overlay">
        <div class="play-button">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </div>
      </div>
    </div>

    <!-- Info -->
    <div class="guide-info">
      <div class="guide-tags" v-if="tagList.length">
        <span v-for="tag in tagList" :key="tag" class="tag-pill" :class="tag.toLowerCase()">
          {{ tag }}
        </span>
      </div>
      <h3 class="guide-title">{{ guide.title }}</h3>
      <p v-if="guide.description" class="guide-description">{{ guide.description }}</p>

      <div class="guide-meta">
        <span class="guide-author">by {{ guide.author_name }}</span>
      </div>
    </div>

    <!-- Admin Actions -->
    <div v-if="authStore.isAdmin" class="admin-actions" @click.stop>
      <button class="action-btn edit-btn" @click="emit('edit', guide)" title="Edit guide" aria-label="Edit guide">
        <Pencil :size="16" />
      </button>
      <button class="action-btn delete-btn" @click="emit('delete', guide)" title="Delete guide" aria-label="Delete guide">
        <Trash2 :size="16" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.guide-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--color-border);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  cursor: pointer;
  position: relative;
}

.guide-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* Thumbnail */
.guide-thumbnail {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
}

.thumbnail-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--transition-base);
}

.guide-card:hover .thumbnail-img {
  transform: scale(1.05);
}

.thumbnail-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-secondary);
}

.placeholder-icon {
  color: var(--color-text-muted);
  opacity: 0.5;
}

/* Type Badge */
.type-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  backdrop-filter: blur(8px);
  z-index: 2;
}

.type-badge.video {
  background: rgba(99, 102, 241, 0.85);
  color: var(--color-text-inverse);
}

.type-badge.written {
  background: rgba(16, 185, 129, 0.85);
  color: var(--color-text-inverse);
}

/* Play overlay for video cards */
.play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.25);
  transition: background var(--transition-fast);
}

.guide-card:hover .play-overlay {
  background: rgba(0, 0, 0, 0.45);
}

.play-button {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--transition-fast);
}

.play-button svg {
  width: 26px;
  height: 26px;
  color: var(--color-accent);
  margin-left: 3px;
}

.guide-card:hover .play-button {
  transform: scale(1.1);
}

/* Info */
.guide-info {
  padding: var(--space-4);
}

.guide-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
}

.tag-pill {
  display: inline-block;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.tag-pill.xkt {
  background: rgba(99, 102, 241, 0.15);
  color: var(--color-tag-xkt);
}

.tag-pill.wtsl {
  background: rgba(34, 197, 94, 0.15);
  color: var(--color-tag-wtsl);
}

.tag-pill.gameplay {
  background: rgba(249, 115, 22, 0.15);
  color: var(--color-tag-gameplay);
}

/* Default tag style for custom tags */
.tag-pill:not(.xkt):not(.wtsl):not(.gameplay) {
  background: rgba(163, 230, 53, 0.15);
  color: var(--color-brand-primary);
}

.guide-title {
  margin: var(--space-2) 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  line-height: 1.3;
}

.guide-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.guide-meta {
  margin-top: var(--space-2);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.guide-author {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

/* Admin Actions */
.admin-actions {
  position: absolute;
  top: 10px;
  left: 10px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity var(--transition-fast);
  z-index: 3;
}

.guide-card:hover .admin-actions {
  opacity: 1;
}

.action-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s ease;
  backdrop-filter: blur(8px);
}

.edit-btn {
  background: rgba(59, 130, 246, 0.85);
  color: var(--color-text-inverse);
}

.edit-btn:hover {
  background: rgba(59, 130, 246, 1);
  transform: scale(1.1);
}

.delete-btn {
  background: rgba(239, 68, 68, 0.85);
  color: var(--color-text-inverse);
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 1);
  transform: scale(1.1);
}
</style>
