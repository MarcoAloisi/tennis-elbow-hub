<script setup>
import { ref } from 'vue'

const props = defineProps({
  filters: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:filters', 'refresh'])

const localSearch = ref(props.filters.searchQuery || '')

function updateFilter(key, value) {
  emit('update:filters', { ...props.filters, [key]: value })
}

function handleSearch() {
  updateFilter('searchQuery', localSearch.value)
}

function clearFilters() {
  localSearch.value = ''
  emit('update:filters', {
    startedOnly: false,
    minElo: null,
    maxElo: null,
    searchQuery: ''
  })
}
</script>

<template>
  <div class="filter-bar">
    <!-- Search -->
    <div class="filter-search">
      <input
        v-model="localSearch"
        type="text"
        placeholder="Search players or tournaments..."
        @keyup.enter="handleSearch"
        @blur="handleSearch"
      />
      <button class="btn btn-icon" @click="handleSearch" title="Search">
        🔍
      </button>
    </div>

    <!-- Started only toggle -->
    <label class="filter-toggle">
      <input 
        type="checkbox"
        :checked="filters.startedOnly"
        @change="updateFilter('startedOnly', $event.target.checked)"
      />
      <span>Live only</span>
    </label>

    <!-- Refresh button -->
    <button class="btn btn-secondary" @click="$emit('refresh')" title="Refresh">
      🔄 Refresh
    </button>

    <!-- Clear filters -->
    <button 
      class="btn btn-ghost" 
      @click="clearFilters"
      v-if="filters.searchQuery || filters.startedOnly"
    >
      Clear
    </button>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-6);
}

.filter-search {
  display: flex;
  flex: 1;
  min-width: 200px;
  max-width: 400px;
}

.filter-search input {
  flex: 1;
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.filter-search .btn-icon {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  border: 1px solid var(--color-border);
  border-left: none;
  background: var(--color-bg-primary);
}

.filter-select {
  min-width: 140px;
}

.filter-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
}

.filter-toggle:hover {
  border-color: var(--color-border-hover);
}

.filter-toggle input {
  accent-color: var(--color-accent);
}

@media (max-width: 768px) {
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-search {
    max-width: none;
  }
}
</style>
