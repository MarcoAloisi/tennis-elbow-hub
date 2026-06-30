<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  avgRating: number | null
  ratingCount: number
  userRating: number | null
  interactive: boolean
}>()

const emit = defineEmits<{ rate: [value: number] }>()

const hovered = ref<number | null>(null)

function activeStars() {
  return hovered.value ?? props.userRating ?? 0
}

function starClass(star: number) {
  return activeStars() >= star ? 'filled' : 'empty'
}
</script>

<template>
  <div class="star-rating">
    <div class="stars" :class="{ interactive }">
      <button
        v-for="star in 5"
        :key="star"
        class="star-btn"
        :class="starClass(star)"
        :disabled="!interactive"
        :aria-label="`Rate ${star} star${star > 1 ? 's' : ''}`"
        @mouseenter="interactive && (hovered = star)"
        @mouseleave="interactive && (hovered = null)"
        @click="interactive && emit('rate', star)"
      >★</button>
    </div>
    <span v-if="ratingCount > 0" class="rating-meta">
      {{ avgRating?.toFixed(1) }} · {{ ratingCount }} {{ ratingCount === 1 ? 'rating' : 'ratings' }}
    </span>
    <span v-else class="rating-meta no-ratings">No ratings yet</span>
  </div>
</template>

<style scoped>
.star-rating {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.stars {
  display: flex;
  gap: 2px;
}

.star-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: 1.1rem;
  line-height: 1;
  color: var(--color-border);
  cursor: default;
  transition: color 0.1s;
}

.star-btn.filled {
  color: #f59e0b;
}

.stars.interactive .star-btn {
  cursor: pointer;
}

.stars.interactive .star-btn:hover,
.stars.interactive .star-btn.filled {
  color: #f59e0b;
}

.rating-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.no-ratings {
  color: var(--color-text-muted);
}
</style>
