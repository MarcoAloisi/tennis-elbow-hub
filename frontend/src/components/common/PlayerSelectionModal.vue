<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  players: {
    type: Array, // Array of { name: 'Name', count: 10 }
    required: true
  },
  isOpen: {
    type: Boolean,
    required: true
  },
  initialSelected: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['confirm', 'cancel'])

const selectedPlayers = ref([])

// Initialize selection when modal opens
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    selectedPlayers.value = [...props.initialSelected]
  }
})

function togglePlayer(name) {
  if (selectedPlayers.value.includes(name)) {
    selectedPlayers.value = selectedPlayers.value.filter(p => p !== name)
  } else {
    selectedPlayers.value.push(name)
  }
}

function confirm() {
  if (selectedPlayers.value.length > 0) {
    emit('confirm', selectedPlayers.value)
  }
}

const sortedPlayers = computed(() => {
    return [...props.players].sort((a, b) => b.count - a.count)
})

const title = computed(() => props.initialSelected.length > 0 ? 'Manage Identity' : 'Who are you?')
const subtitle = computed(() => props.initialSelected.length > 0 ? 'Update the player name(s) that represent YOU.' : 'Select the player name(s) that represent YOU in the logs.')
</script>

<template>
  <div v-if="isOpen" class="modal-overlay">
    <div class="modal-content">
      <h2>{{ title }}</h2>
      <p class="subtitle">{{ subtitle }}</p>
      
      <div class="players-list">
        <div 
          v-for="p in sortedPlayers" 
          :key="p.name"
          class="player-item"
          :class="{ selected: selectedPlayers.includes(p.name) }"
          @click="togglePlayer(p.name)"
        >
          <div class="player-info">
             <span class="name">{{ p.name }}</span>
             <span class="count">{{ p.count }} matches</span>
          </div>
          <div class="checkbox">
            <span v-if="selectedPlayers.includes(p.name)">✅</span>
            <span v-else class="empty-box"></span>
          </div>
        </div>
      </div>

      <div class="actions">
        <!-- <button class="btn btn-secondary" @click="emit('cancel')">Cancel</button> -->
        <button 
          class="btn btn-primary" 
          :disabled="selectedPlayers.length === 0"
          @click="confirm"
        >
          Confirm Identity
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: var(--color-bg-card);
  padding: var(--space-8);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 500px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--color-border);
}

h2 {
    margin-bottom: var(--space-2);
    text-align: center;
}

.subtitle {
    color: var(--color-text-muted);
    text-align: center;
    margin-bottom: var(--space-6);
}

.players-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    margin-bottom: var(--space-6);
    padding-right: var(--space-2);
}

.player-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-4);
    background: var(--color-bg-secondary);
    border: 2px solid transparent;
    border-radius: var(--radius-lg);
    cursor: pointer;
    transition: all var(--transition-fast);
}

.player-item:hover {
    background: var(--color-bg-hover);
}

.player-item.selected {
    border-color: var(--color-accent);
    background: rgba(var(--color-accent-rgb), 0.1);
}

.player-info {
    display: flex;
    flex-direction: column;
}

.name {
    font-weight: bold;
    font-size: var(--font-size-md);
}

.count {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
}

.checkbox {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.empty-box {
    width: 20px;
    height: 20px;
    border: 2px solid var(--color-text-muted);
    border-radius: 4px;
}

.actions {
    display: flex;
    justify-content: center;
    gap: var(--space-4);
}

.btn {
    width: 100%;
    padding: var(--space-3);
    font-size: var(--font-size-md);
}
</style>
