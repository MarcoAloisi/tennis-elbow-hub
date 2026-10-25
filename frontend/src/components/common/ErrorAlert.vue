<script setup lang="ts">
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-vue-next'
defineProps({
  type: {
    type: String,
    default: 'error',
    validator: (v: string) => ['error', 'warning', 'info', 'success'].includes(v)
  },
  message: {
    type: String,
    required: true
  },
  dismissible: {
    type: Boolean,
    default: true
  }
})

defineEmits(['dismiss'])

const icons = {
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
  success: CheckCircle2
}
</script>

<template>
  <div class="alert" :class="`alert-${type}`" role="alert">
    <component :is="icons[type]" class="alert-icon" :size="18" aria-hidden="true" />
    <span class="alert-message">{{ message }}</span>
    <button 
      v-if="dismissible" 
      class="alert-dismiss" 
      @click="$emit('dismiss')"
      aria-label="Dismiss"
    >
      ✕
    </button>
  </div>
</template>

<style scoped>
.alert {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  animation: slideIn 0.2s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.alert-error {
  background: var(--color-error-light);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.alert-warning {
  background: var(--color-warning-light);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.alert-info {
  background: var(--color-info-light);
  color: var(--color-info);
  border: 1px solid var(--color-info);
}

.alert-success {
  background: var(--color-success-light);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.alert-icon {
  flex-shrink: 0;
}

.alert-message {
  flex: 1;
}

.alert-dismiss {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  opacity: 0.7;
  transition: opacity var(--transition-fast);
}

.alert-dismiss:hover {
  opacity: 1;
}
</style>
