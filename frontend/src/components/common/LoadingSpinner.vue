<script setup>
defineProps({
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v)
  }
})
</script>

<template>
  <div class="spinner-container" :class="`size-${size}`">
    <div class="spinner"></div>
  </div>
</template>

<style scoped>
.spinner-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner {
  border-radius: 50%;
  border-style: solid;
  border-color: var(--color-border);
  border-top-color: var(--color-accent);
  animation: spin 0.8s linear infinite;
}

.size-sm .spinner {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

.size-md .spinner {
  width: 24px;
  height: 24px;
  border-width: 3px;
}

.size-lg .spinner {
  width: 40px;
  height: 40px;
  border-width: 4px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
