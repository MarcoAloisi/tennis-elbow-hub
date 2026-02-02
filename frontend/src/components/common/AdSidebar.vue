<script setup>
defineProps({
  side: {
    type: String,
    validator: (value) => ['left', 'right'].includes(value),
    required: true
  }
})
</script>

<template>
  <div class="ad-sidebar" :class="side">
    <div class="ad-mock-content">
      <div class="ad-label">Advertisement</div>
      
      <!-- 
        AD CONFIGURATION INSTRUCTIONS:
        1. Sign up for an ad provider (e.g., Google AdSense).
        2. Get the "Ad Unit" code (usually a <script> tag).
        3. Replace the .ad-placeholder div below with that code.
        4. Alternatively, you can use a distinct component for the ad unit if using a Vue-specific ad library.
      -->
      
      <!-- Placeholder for actual ad code - REPLACE THIS BLOCK -->
      <div class="ad-placeholder">
        <span>Ad Space</span>
      </div>
      <!-- End Placeholder -->
      
    </div>
  </div>
</template>

<style scoped>
.ad-sidebar {
  width: 100%;
  height: 100%;
  padding-top: var(--space-4);
  display: flex;
  flex-direction: column;
}

.ad-sidebar.left {
  align-items: flex-end; /* Push content towards main content */
}

.ad-sidebar.right {
  align-items: flex-start; /* Push content towards main content */
}

.ad-mock-content {
  width: 160px; /* Standard Skyscraper width */
  min-height: 600px; /* Standard Skyscraper height */
  background-color: var(--color-bg-secondary);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  position: sticky;
  top: 100px; /* Sticky below header */
  opacity: 0.6;
  transition: opacity 0.3s ease;
}

.ad-mock-content:hover {
  opacity: 1;
}

.ad-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  margin-bottom: var(--space-4);
  letter-spacing: 0.05em;
  opacity: 0.7;
}

.ad-placeholder {
  width: 120px;
  height: 120px;
  border: 2px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 0.8rem;
}
</style>
