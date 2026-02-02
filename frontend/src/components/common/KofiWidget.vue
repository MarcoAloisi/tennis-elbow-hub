<script setup>
defineProps({
  username: {
    type: String,
    default: 'tenniselbowhub' // Default username, user should update this
  }
})
</script>

<template>
  <a 
    class="kofi-widget"
    :href="`https://ko-fi.com/${username}`" 
    target="_blank"
    rel="noopener noreferrer"
  >
    <div class="kofi-icon">
      <!-- Simple heart shape often associated with Ko-fi -->
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="heart-svg">
        <path d="M2.004 9.601l.496-5.65C2.66 2.376 3.996 1.157 5.568 1.157h9.049c1.572 0 2.908 1.22 3.068 2.793l.496 5.65a5.57 5.57 0 0 1-2.905 5.253 2.016 2.016 0 0 0 1.942 1.487h-10.43c.957 0 1.764-.675 1.942-1.487a5.57 5.57 0 0 1-2.905-5.253zM15.918 13.91l-.22-2.502c-.08-.916.643-1.688 1.56-1.688.85 0 1.558.653 1.636 1.498l.205 2.196c.094 1.002-.577 1.92-1.539 2.1l-.813.153a1.644 1.644 0 0 1-1.928-1.564l1.1.192.812-.153c.12-.023.204-.138.192-.264l-.204-2.196a.14.14 0 0 0-.135-.125c-.076 0-.137.064-.13.14l.22 2.502a.14.14 0 0 1-.165.132l-1.1-.192A.144.144 0 0 0 15 13.145z"/>
        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
      </svg>
    </div>
    <span class="kofi-text">Support on Ko-fi</span>
  </a>
</template>

<style scoped>
.kofi-widget {
  position: fixed;
  bottom: var(--space-6);
  right: var(--space-6);
  z-index: 100;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background-color: #29abe0; /* Ko-fi Blue */
  color: #FFFFFF;
  padding: 10px 16px;
  border-radius: 9999px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  text-decoration: none;
  font-family: var(--font-heading);
  font-weight: 600;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s;
  border: 1px solid rgba(255,255,255,0.1);
}

.kofi-widget:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.15), 0 4px 6px -2px rgba(0, 0, 0, 0.1);
  background-color: #1a9bd0;
}

.kofi-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.heart-svg {
  width: 20px;
  height: 20px;
  fill: #FFFFFF;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); }
  10% { transform: scale(1.1); }
  20% { transform: scale(1); }
  100% { transform: scale(1); }
}

.kofi-text {
  font-size: 0.95rem;
  letter-spacing: 0.01em;
}

/* Dark mode compatibility */
[data-theme="dark"] .kofi-widget {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
}
</style>
