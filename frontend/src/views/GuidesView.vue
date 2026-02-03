<script setup>
import { ref, computed } from 'vue'
import guidesData from '@/data/guides.json'
import VideoCard from '@/components/guides/VideoCard.vue'

const selectedCategory = ref('all')

const filteredVideos = computed(() => {
  if (selectedCategory.value === 'all') {
    return guidesData.videos
  }
  return guidesData.videos.filter(v => v.category === selectedCategory.value)
})
</script>

<template>
  <div class="guides-view">
    <!-- Header -->
    <div class="page-header">
      <h1>Guides</h1>
      <p>Video tutorials to help you get started with Tennis Elbow 4 online play.</p>
    </div>

    <!-- Category Filters -->
    <div class="category-filters">
      <button 
        v-for="category in guidesData.categories" 
        :key="category.id"
        class="category-btn"
        :class="{ active: selectedCategory === category.id }"
        @click="selectedCategory = category.id"
      >
        <span class="category-icon">{{ category.icon }}</span>
        {{ category.label }}
      </button>
    </div>

    <!-- Video Grid -->
    <div class="videos-grid">
      <VideoCard 
        v-for="video in filteredVideos" 
        :key="video.id"
        :video="video"
      />
    </div>

    <!-- Empty State -->
    <div v-if="filteredVideos.length === 0" class="empty-state">
      <span class="empty-icon">🎬</span>
      <p>No guides found in this category.</p>
    </div>
  </div>
</template>

<style scoped>
.guides-view {
  min-height: 100%;
}

.page-header {
  margin-bottom: var(--space-6);
}

.page-header h1 {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.page-header p {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

/* Category Filters */
.category-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
}

.category-btn {
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

.category-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.category-btn.active {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: white;
}

.category-icon {
  font-size: 1rem;
}

/* Video Grid */
.videos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-6);
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--space-12);
  color: var(--color-text-secondary);
}

.empty-icon {
  font-size: 4rem;
  display: block;
  margin-bottom: var(--space-4);
}

/* Responsive */
@media (max-width: 640px) {
  .videos-grid {
    grid-template-columns: 1fr;
  }

  .category-filters {
    justify-content: center;
  }
}
</style>
