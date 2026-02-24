<script setup>
import { onMounted, computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGuidesStore } from '@/stores/guides'

const route = useRoute()
const router = useRouter()
const guidesStore = useGuidesStore()

const isVideoPlaying = ref(false)

onMounted(() => {
  guidesStore.fetchGuide(route.params.slug)
})

const guide = computed(() => guidesStore.currentGuide)
const isVideo = computed(() => guide.value?.guide_type === 'video')

const tagList = computed(() => {
  if (!guide.value?.tags) return []
  return guide.value.tags.split(',').map(t => t.trim()).filter(Boolean)
})

const youtubeId = computed(() => {
  if (!guide.value?.youtube_url) return null
  const match = guide.value.youtube_url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/)
  return match ? match[1] : null
})

const thumbnailUrl = computed(() => {
  if (guide.value?.thumbnail_url) return guide.value.thumbnail_url
  if (youtubeId.value) return `https://img.youtube.com/vi/${youtubeId.value}/maxresdefault.jpg`
  return null
})

const formattedDate = computed(() => {
  if (!guide.value?.created_at) return ''
  return new Date(guide.value.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
})

function goBack() {
  router.push({ name: 'Guides' })
}

function playVideo() {
  isVideoPlaying.value = true
}
</script>

<template>
  <div class="guide-detail-view">
    <!-- Loading state -->
    <div v-if="guidesStore.loading" class="loading-container">
      <div class="loading-spinner"></div>
      <p>Loading guide...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="guidesStore.error" class="error-container">
      <span class="error-icon">⚠️</span>
      <h2>Guide not found</h2>
      <p>{{ guidesStore.error }}</p>
      <button class="btn-back" @click="goBack">← Back to Guides</button>
    </div>

    <!-- Guide content -->
    <article v-else-if="guide" class="guide-article">
      <!-- Back link -->
      <button class="btn-back" @click="goBack">← Back to Guides</button>

      <!-- Video Player / Header Image -->
      <div v-if="isVideo" class="video-container">
        <div v-if="!isVideoPlaying" class="video-thumbnail" @click="playVideo">
          <img v-if="thumbnailUrl" :src="thumbnailUrl" :alt="guide.title" class="thumbnail-img" />
          <div class="play-overlay">
            <div class="play-button">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z"/>
              </svg>
            </div>
          </div>
        </div>
        <div v-else class="video-embed">
          <iframe
            :src="`https://www.youtube.com/embed/${youtubeId}?autoplay=1&rel=0`"
            title="YouTube video player"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
          ></iframe>
        </div>
      </div>

      <div v-else-if="thumbnailUrl" class="header-image">
        <img :src="thumbnailUrl" :alt="guide.title" />
      </div>

      <!-- Article Header -->
      <header class="article-header">
        <div class="article-tags" v-if="tagList.length">
          <span v-for="tag in tagList" :key="tag" class="tag-pill" :class="tag.toLowerCase()">
            {{ tag }}
          </span>
          <span class="type-badge" :class="guide.guide_type">
            {{ isVideo ? '📹 Video' : '📖 Article' }}
          </span>
        </div>
        <h1 class="article-title">{{ guide.title }}</h1>
        <div class="article-meta">
          <span class="meta-author">By <strong>{{ guide.author_name }}</strong></span>
          <span class="meta-divider">·</span>
          <span class="meta-date">{{ formattedDate }}</span>
        </div>
        <p v-if="guide.description" class="article-description">{{ guide.description }}</p>
      </header>

      <!-- Written content -->
      <div v-if="!isVideo && guide.content" class="article-body" v-html="guide.content"></div>
    </article>
  </div>
</template>

<style scoped>
.guide-detail-view {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
  min-height: 100%;
}

.loading-container,
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: var(--color-text-secondary);
  gap: var(--space-4);
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

.error-icon {
  font-size: 3rem;
}

/* Back button */
.btn-back {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 8px 16px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: 600;
  transition: all 0.2s ease;
  margin-bottom: var(--space-6);
}

.btn-back:hover {
  color: var(--color-text-primary);
  border-color: var(--color-brand-primary);
}

/* Video */
.video-container {
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-6);
}

.video-thumbnail {
  position: relative;
  aspect-ratio: 16 / 9;
  cursor: pointer;
  overflow: hidden;
}

.thumbnail-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.video-thumbnail:hover .thumbnail-img {
  transform: scale(1.03);
}

.play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  transition: background 0.2s ease;
}

.video-thumbnail:hover .play-overlay {
  background: rgba(0, 0, 0, 0.5);
}

.play-button {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease;
}

.play-button svg {
  width: 36px;
  height: 36px;
  color: var(--color-accent);
  margin-left: 4px;
}

.video-thumbnail:hover .play-button {
  transform: scale(1.1);
}

.video-embed {
  position: relative;
  aspect-ratio: 16 / 9;
}

.video-embed iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

/* Header image for written guides */
.header-image {
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-6);
}

.header-image img {
  width: 100%;
  height: auto;
  display: block;
}

/* Article Header */
.article-header {
  margin-bottom: var(--space-8);
  padding-bottom: var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.article-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.tag-pill {
  display: inline-block;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.tag-pill.xkt { background: rgba(99, 102, 241, 0.15); color: #6366f1; }
.tag-pill.wtsl { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
.tag-pill.gameplay { background: rgba(249, 115, 22, 0.15); color: #f97316; }
.tag-pill:not(.xkt):not(.wtsl):not(.gameplay) {
  background: rgba(163, 230, 53, 0.15);
  color: var(--color-brand-primary);
}

.type-badge {
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}

.type-badge.video { background: rgba(99, 102, 241, 0.15); color: #6366f1; }
.type-badge.written { background: rgba(16, 185, 129, 0.15); color: #10b981; }

.article-title {
  font-family: var(--font-heading);
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text-primary);
  line-height: 1.2;
  margin: 0 0 var(--space-3) 0;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: var(--space-3);
}

.meta-divider {
  opacity: 0.4;
}

.article-description {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
}

/* Article Body (rendered HTML) */
.article-body {
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  line-height: 1.8;
}

.article-body :deep(h2) {
  font-family: var(--font-heading);
  font-size: var(--font-size-2xl);
  font-weight: 700;
  margin: 2em 0 0.8em;
  color: var(--color-text-primary);
}

.article-body :deep(h3) {
  font-family: var(--font-heading);
  font-size: var(--font-size-xl);
  font-weight: 600;
  margin: 1.5em 0 0.6em;
  color: var(--color-text-primary);
}

.article-body :deep(p) {
  margin: 0.8em 0;
}

.article-body :deep(a) {
  color: var(--color-brand-primary);
  text-decoration: underline;
  transition: opacity 0.15s ease;
}

.article-body :deep(a:hover) {
  opacity: 0.8;
}

.article-body :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-lg);
  margin: 1.5em 0;
  box-shadow: var(--shadow-md);
}

.article-body :deep(ul),
.article-body :deep(ol) {
  padding-left: 1.5em;
  margin: 0.8em 0;
}

.article-body :deep(li) {
  margin: 0.3em 0;
}

.article-body :deep(blockquote) {
  border-left: 4px solid var(--color-brand-primary);
  padding: var(--space-4) var(--space-4);
  margin: 1.5em 0;
  background: var(--color-bg-secondary);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: var(--color-text-secondary);
  font-style: italic;
}

.article-body :deep(pre) {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  overflow-x: auto;
  font-family: 'Fira Code', monospace;
  font-size: var(--font-size-sm);
  margin: 1.5em 0;
}

.article-body :deep(code) {
  background: var(--color-bg-secondary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
}

.article-body :deep(pre code) {
  background: none;
  padding: 0;
}

/* Responsive */
@media (max-width: 640px) {
  .article-title {
    font-size: 1.5rem;
  }

  .article-meta {
    flex-wrap: wrap;
  }
}
</style>
