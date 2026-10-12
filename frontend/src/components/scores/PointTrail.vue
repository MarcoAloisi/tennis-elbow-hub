<script setup lang="ts">
import { computed } from 'vue'
import { POINT_TAGS, splitPoint } from '@/utils/gameLog'

const props = defineProps<{ points: string[] }>()

const parts = computed(() => props.points.map(splitPoint))
</script>

<template>
  <template v-for="(part, i) in parts" :key="i">
    <span>{{ part.score }}<template v-for="tag in part.tags" :key="tag">{{ ' ' }}<abbr class="point-tag" :title="POINT_TAGS[tag]">{{ tag }}</abbr></template></span><template v-if="i < parts.length - 1">, </template>
  </template>
</template>

<style scoped>
.point-tag {
  padding: 0 var(--space-1);
  border-radius: var(--radius-sm);
  background: var(--color-warning-light);
  color: var(--color-warning);
  font-weight: var(--font-weight-bold);
  text-decoration: none;
  cursor: help;
}
</style>
