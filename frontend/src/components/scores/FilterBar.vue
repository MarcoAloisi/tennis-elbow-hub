<script setup lang="ts">
import { ref } from 'vue'
import { Search, RefreshCw } from 'lucide-vue-next'

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
    <label class="filter-search">
      <Search :size="16" aria-hidden="true" />
      <input
        v-model="localSearch"
        type="search"
        placeholder="Search players or tournaments"
        aria-label="Search players or tournaments"
        @keyup.enter="handleSearch"
        @blur="handleSearch"
      />
    </label>

    <div class="seg" role="group" aria-label="Show matches">
      <button type="button" :aria-pressed="!filters.startedOnly" @click="updateFilter('startedOnly', false)">All</button>
      <button type="button" :aria-pressed="!!filters.startedOnly" @click="updateFilter('startedOnly', true)">Live only</button>
    </div>

    <button type="button" class="icon-btn" @click="$emit('refresh')" title="Refresh" aria-label="Refresh">
      <RefreshCw :size="16" />
    </button>

    <button
      type="button"
      class="clear-btn"
      @click="clearFilters"
      v-if="filters.searchQuery"
    >
      Clear search
    </button>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.filter-search {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 40px;
  min-width: 260px;
  padding: 0 var(--space-3);
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
}

.filter-search:focus-within {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}

.filter-search input {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.filter-search input:focus {
  outline: none;
  box-shadow: none;
}

.icon-btn {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.icon-btn:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.clear-btn {
  height: 40px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
}

.clear-btn:hover {
  color: var(--color-text-primary);
}

.seg {
  display: inline-flex;
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  padding: 3px;
}

.seg button {
  display: inline-flex;
  align-items: center;
  height: 34px;
  padding: 0 var(--space-4);
  border-radius: 6px;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.seg button:hover {
  color: var(--color-text-primary);
}

.seg button[aria-pressed="true"] {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

@media (max-width: 768px) {
  .filter-bar {
    width: 100%;
  }

  .filter-search {
    flex: 1;
    min-width: 0;
  }
}
</style>
