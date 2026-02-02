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
      
      <!-- TE4 Ad Unit -->
      <ins class="adsbygoogle"
           style="display:block"
           data-ad-client="ca-pub-7154517961345659"
           data-ad-slot="6495286119"
           data-ad-format="auto"
           data-full-width-responsive="true"></ins>
      <script>
           (adsbygoogle = window.adsbygoogle || []).push({});
      </script>
      
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
