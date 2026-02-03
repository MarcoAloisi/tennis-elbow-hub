<script setup>
import { ref } from 'vue'

const props = defineProps({
  video: {
    type: Object,
    required: true
  }
})

const isPlaying = ref(false)

// Generate YouTube thumbnail URL
const thumbnailUrl = `https://img.youtube.com/vi/${props.video.youtubeId}/maxresdefault.jpg`

function playVideo() {
  isPlaying.value = true
}
</script>

<template>
  <div class="video-card">
    <!-- Thumbnail/Preview State -->
    <div v-if="!isPlaying" class="video-thumbnail" @click="playVideo">
      <img :src="thumbnailUrl" :alt="video.title" class="thumbnail-img" />
      <div class="play-overlay">
        <div class="play-button">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </div>
      </div>
    </div>

    <!-- YouTube Embed (Lazy Loaded) -->
    <div v-else class="video-embed">
      <iframe
        :src="`https://www.youtube.com/embed/${video.youtubeId}?autoplay=1&rel=0`"
        title="YouTube video player"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
      ></iframe>
    </div>

    <!-- Video Info -->
    <div class="video-info">
      <span class="video-category" :class="video.category">
        {{ video.category.toUpperCase() }}
      </span>
      <h3 class="video-title">{{ video.title }}</h3>
      <p class="video-description">{{ video.description }}</p>
    </div>
  </div>
</template>

<style scoped>
.video-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--color-border);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.video-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
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
  transition: transform var(--transition-base);
}

.video-thumbnail:hover .thumbnail-img {
  transform: scale(1.05);
}

.play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  transition: background var(--transition-fast);
}

.video-thumbnail:hover .play-overlay {
  background: rgba(0, 0, 0, 0.5);
}

.play-button {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--transition-fast);
}

.play-button svg {
  width: 32px;
  height: 32px;
  color: var(--color-accent);
  margin-left: 4px; /* Visual centering for play icon */
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

.video-info {
  padding: var(--space-4);
}

.video-category {
  display: inline-block;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.video-category.xkt {
  background: rgba(99, 102, 241, 0.15);
  color: #6366f1;
}

.video-category.wtsl {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.video-category.gameplay {
  background: rgba(249, 115, 22, 0.15);
  color: #f97316;
}

.video-title {
  margin: var(--space-2) 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.video-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
}
</style>
