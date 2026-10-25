<script setup lang="ts">
const still =
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

defineProps<{
  tour: 'xkt' | 'wtsl'
  href: string
  label: string
}>()
</script>

<template>
  <a
    class="tour-promo"
    :href="href"
    target="_blank"
    rel="noopener"
    :aria-label="`${label} (opens in a new tab)`"
  >
    <video
      class="tour-promo-media"
      :poster="`/tours/${tour}.jpg`"
      :autoplay="!still"
      muted
      loop
      playsinline
      preload="metadata"
      aria-hidden="true"
    >
      <source :src="`/tours/${tour}.webm`" type="video/webm" />
      <source :src="`/tours/${tour}.mp4`" type="video/mp4" />
    </video>
    <span class="tour-promo-cta">{{ label }}</span>
  </a>
</template>

<style scoped>
.tour-promo {
  position: sticky;
  top: 100px;
  display: block;
  width: 160px;
  height: 600px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: #0B1210;
}

.tour-promo-media {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.tour-promo-cta {
  position: absolute;
  left: var(--space-3);
  right: var(--space-3);
  bottom: var(--space-4);
  padding: var(--space-2);
  white-space: nowrap;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  text-align: center;
  transition: background var(--transition-fast);
}

.tour-promo:hover .tour-promo-cta,
.tour-promo:focus-visible .tour-promo-cta {
  background: rgba(255, 255, 255, 0.24);
}

.tour-promo:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
</style>
