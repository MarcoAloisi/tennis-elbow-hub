<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useResults } from '@/composables/useResults'
import { usePagination } from '@/composables/usePagination'
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import ResultCard from './ResultCard.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { Activity } from 'lucide-vue-next'

const MODS: { value: string | null; label: string }[] = [
  { value: null, label: 'All' },
  { value: 'xkt', label: 'XKT' },
  { value: 'wtsl', label: 'WTSL' },
  { value: 'vanilla', label: 'Vanilla' },
]

function toLocalISO(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function todayLocalISO(): string {
  return toLocalISO(new Date())
}

const dateStr = ref(todayLocalISO())
const mod = ref<string | null>(null)
const page = ref(1)

const { results, total, totalPages, isLoading, error, fetchResults } = useResults()

function load() {
  fetchResults({ date: dateStr.value, mod: mod.value, player: searchQuery.value, page: page.value })
}

const { searchQuery } = useDebouncedSearch(() => {
  page.value = 1
  load()
})

function shiftDay(delta: number) {
  const d = new Date(`${dateStr.value}T00:00:00`)
  d.setDate(d.getDate() + delta)
  const shifted = toLocalISO(d)
  if (shifted > todayLocalISO()) return
  dateStr.value = shifted
}

function goToday() {
  dateStr.value = todayLocalISO()
}

function setMod(value: string | null) {
  mod.value = value
  page.value = 1
  load()
}

const isToday = computed(() => dateStr.value === todayLocalISO())

watch(dateStr, () => {
  page.value = 1
  load()
})

const { pageNumbers, showingRange, goToPage } = usePagination({
  currentPage: () => page.value,
  totalPages: () => totalPages.value,
  totalItems: () => total.value,
  pageSize: 50,
  onPageChange: (p: number) => {
    page.value = p
    load()
  },
})

onMounted(load)
</script>

<template>
  <div class="results-tab">
    <div class="results-filters">
      <div class="day-nav">
        <button class="btn btn-icon" @click="shiftDay(-1)" aria-label="Previous day" title="Previous day">‹</button>
        <input
          type="date"
          v-model="dateStr"
          :max="todayLocalISO()"
          class="day-input"
          aria-label="Select day"
        />
        <button
          class="btn btn-icon"
          @click="shiftDay(1)"
          :disabled="isToday"
          aria-label="Next day"
          title="Next day"
        >
          ›
        </button>
        <button v-if="!isToday" class="btn btn-ghost" @click="goToday">Today</button>
      </div>

      <div class="mod-pills">
        <button
          v-for="m in MODS"
          :key="m.label"
          class="mod-pill"
          :class="{ active: mod === m.value }"
          @click="setMod(m.value)"
        >
          {{ m.label }}
        </button>
      </div>

      <input
        v-model="searchQuery"
        type="text"
        class="player-search"
        placeholder="Search players..."
        aria-label="Search players"
      />
    </div>

    <ErrorAlert v-if="error" :message="error" type="error" />

    <div v-if="isLoading && !results.length" class="loading-state">
      <LoadingSpinner size="lg" />
      <p>Loading results...</p>
    </div>

    <div v-else-if="!results.length" class="empty-state">
      <div class="empty-icon-wrapper">
        <Activity class="empty-icon" :size="64" :stroke-width="1.5" />
      </div>
      <h3>No results found</h3>
      <p>No finished matches for this day{{ mod || searchQuery ? ' with these filters' : '' }}.</p>
    </div>

    <div v-else class="results-list">
      <ResultCard v-for="r in results" :key="r.match_id" :result="r" />
    </div>

    <div v-if="totalPages > 1" class="pagination-container">
      <span class="pagination-info">
        Showing {{ showingRange.from }}–{{ showingRange.to }} of {{ showingRange.total }}
      </span>
      <div class="pagination-controls">
        <button
          class="page-btn nav-btn"
          :disabled="page <= 1"
          @click="goToPage(page - 1)"
          aria-label="Previous page"
        >
          ‹
        </button>
        <template v-for="(p, idx) in pageNumbers" :key="idx">
          <span v-if="p === '...'" class="page-ellipsis">…</span>
          <button
            v-else
            class="page-btn"
            :class="{ active: p === page }"
            @click="goToPage(p)"
          >
            {{ p }}
          </button>
        </template>
        <button
          class="page-btn nav-btn"
          :disabled="page >= totalPages"
          @click="goToPage(page + 1)"
          aria-label="Next page"
        >
          ›
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.results-tab {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.results-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.day-nav {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.day-input {
  min-width: 150px;
}

.mod-pills {
  display: flex;
  gap: var(--space-2);
}

.mod-pill {
  padding: var(--space-1) var(--space-4);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-muted);
  background: transparent;
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mod-pill:hover {
  color: var(--color-text-primary);
}

.mod-pill.active {
  color: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
  background: var(--color-bg-secondary);
}

.player-search {
  flex: 1;
  min-width: 180px;
  max-width: 320px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-16);
  gap: var(--space-4);
  color: var(--color-text-muted);
  text-align: center;
}

.empty-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  box-shadow: 0 0 20px rgba(34, 197, 94, 0.2);
}

[data-theme='dark'] .empty-icon-wrapper {
  color: var(--color-brand-primary);
  background: rgba(212, 255, 95, 0.1);
  box-shadow: 0 0 20px rgba(212, 255, 95, 0.15);
}
</style>
